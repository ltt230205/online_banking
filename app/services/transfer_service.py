from datetime import UTC, datetime
from decimal import Decimal
import secrets

from sqlalchemy.orm import Session

from app.config import settings
from app.core.exceptions import AppError, forbidden, not_found
from app.models.entities import Transaction, TransactionEntry, User
from app.repositories.account_repository import AccountRepository
from app.repositories.customer_repository import CustomerRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.transaction import TransferRequest
from app.services.audit_service import add_audit
from app.services.notification_service import NotificationService
from app.services.otp_service import OtpService


class InterbankGateway:
    def transfer(self, *, transaction_code: str, account_number: str, bank_code: str, amount: Decimal) -> dict[str, object]:
        return {"success": True, "reference": f"EXT-{transaction_code}"}


class TransferService:
    INTERNAL_BANK_CODES = {"OUR_BANK", "LOCAL"}

    def __init__(self, session: Session) -> None:
        self.session = session
        self.accounts = AccountRepository(session)
        self.customers = CustomerRepository(session)
        self.transactions = TransactionRepository(session)
        self.otp = OtpService(session)

    def _customer(self, user_id: int):
        customer = self.customers.get_by_user_id(user_id)
        if customer is None:
            raise not_found("CUSTOMER_NOT_FOUND", "Customer profile not found")
        if customer.kyc_status != "VERIFIED":
            raise AppError("KYC_NOT_VERIFIED", "Customer KYC must be verified", 403)
        return customer

    def create(self, user: User, data: TransferRequest) -> tuple[Transaction, str]:
        customer = self._customer(user.id)
        source = self.accounts.get(data.source_account_id)
        if source is None or source.customer_id != customer.id:
            raise not_found("ACCOUNT_NOT_FOUND", "Source account not found")
        if source.status != "ACTIVE":
            raise AppError("ACCOUNT_LOCKED", "Source account is not active", 409)
        if source.balance < data.amount:
            raise AppError("INSUFFICIENT_BALANCE", "Account balance is insufficient", 409)
        internal = data.bank_code.upper() in self.INTERNAL_BANK_CODES
        destination = self.accounts.get_by_number(data.destination_account_number) if internal else None
        if internal and destination is None:
            raise not_found("ACCOUNT_NOT_FOUND", "Destination account not found")
        if destination and destination.id == source.id:
            raise AppError("SAME_ACCOUNT_TRANSFER", "Cannot transfer to the same account", 422)
        if destination and (destination.status != "ACTIVE" or destination.currency != source.currency):
            raise AppError("DESTINATION_ACCOUNT_INVALID", "Destination account is not available", 409)
        transaction = Transaction(
            transaction_code=f"TXN-{secrets.token_hex(8).upper()}",
            transaction_type="INTERNAL_TRANSFER" if internal else "INTERBANK_TRANSFER",
            status="PENDING",
            source_account_id=source.id,
            destination_account_id=destination.id if destination else None,
            destination_account_number=data.destination_account_number,
            destination_bank_code=data.bank_code.upper(),
            destination_account_name=destination.customer.full_name if destination else None,
            amount=data.amount,
            fee=Decimal("0"),
            currency=source.currency,
            description=data.description,
            initiated_by=user.id,
        )
        self.session.add(transaction)
        self.session.flush()
        code = self.otp.create(user_id=user.id, purpose="TRANSFER", transaction_id=transaction.id)
        add_audit(
            self.session,
            user_id=user.id,
            action="TRANSFER_CREATED",
            resource_type="transactions",
            resource_id=transaction.id,
            after={"status": transaction.status, "amount": str(transaction.amount)},
        )
        self.session.commit()
        self.session.refresh(transaction)
        return transaction, code

    def verify_and_execute(self, user: User, transaction_id: int, otp_code: str) -> Transaction:
        customer = self._customer(user.id)
        transaction = self.transactions.get(transaction_id, lock=True)
        if transaction is None:
            raise not_found("TRANSACTION_NOT_FOUND", "Transaction not found")
        source = self.accounts.get(transaction.source_account_id) if transaction.source_account_id else None
        if source is None or source.customer_id != customer.id:
            raise forbidden()
        if transaction.status in {"SUCCESS", "FAILED", "CANCELLED"}:
            raise AppError("TRANSACTION_ALREADY_COMPLETED", "Transaction is already completed", 409)
        self.otp.verify(
            user_id=user.id,
            purpose="TRANSFER",
            code=otp_code,
            transaction_id=transaction.id,
        )
        account_ids = [source.id]
        if transaction.destination_account_id:
            account_ids.append(transaction.destination_account_id)
        locked = self.accounts.lock_accounts(account_ids)
        source = locked.get(source.id)
        destination = locked.get(transaction.destination_account_id) if transaction.destination_account_id else None
        if source is None or source.status != "ACTIVE":
            raise AppError("ACCOUNT_LOCKED", "Source account is not active", 409)
        debit_amount = transaction.amount + transaction.fee
        if source.balance < debit_amount:
            raise AppError("INSUFFICIENT_BALANCE", "Account balance is insufficient", 409)
        source_before = source.balance
        if transaction.transaction_type == "INTERBANK_TRANSFER":
            result = InterbankGateway().transfer(
                transaction_code=transaction.transaction_code,
                account_number=transaction.destination_account_number or "",
                bank_code=transaction.destination_bank_code or "",
                amount=transaction.amount,
            )
            if not result["success"]:
                transaction.status = "FAILED"
                transaction.failure_reason = "External bank rejected the transfer"
                add_audit(self.session, user_id=user.id, action="TRANSFER_FAILED", resource_type="transactions", resource_id=transaction.id)
                self.session.commit()
                return transaction
        elif destination is None or destination.status != "ACTIVE":
            raise AppError("DESTINATION_ACCOUNT_INVALID", "Destination account is not active", 409)
        source.balance -= debit_amount
        source.version += 1
        self.session.add(
            TransactionEntry(
                transaction_id=transaction.id,
                account_id=source.id,
                entry_type="DEBIT",
                amount=debit_amount,
                balance_before=source_before,
                balance_after=source.balance,
            )
        )
        if destination:
            destination_before = destination.balance
            destination.balance += transaction.amount
            destination.version += 1
            self.session.add(
                TransactionEntry(
                    transaction_id=transaction.id,
                    account_id=destination.id,
                    entry_type="CREDIT",
                    amount=transaction.amount,
                    balance_before=destination_before,
                    balance_after=destination.balance,
                )
            )
        transaction.status = "SUCCESS"
        transaction.completed_at = datetime.now(UTC)
        add_audit(self.session, user_id=user.id, action="TRANSFER_SUCCESS", resource_type="transactions", resource_id=transaction.id)
        NotificationService(self.session).create_in_app(
            user.id, "TRANSFER_SUCCESS", "Chuyển khoản thành công", f"Giao dịch {transaction.transaction_code} đã thành công."
        )
        self.session.commit()
        self.session.refresh(transaction)
        return transaction

    @staticmethod
    def expose_otp(code: str) -> str | None:
        return code if settings.app_env.lower() == "development" else None
