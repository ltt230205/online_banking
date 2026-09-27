from datetime import UTC, datetime
from decimal import Decimal
import secrets

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import AppError, forbidden, not_found
from app.repositories.account_repository import AccountRepository
from app.repositories.customer_repository import CustomerRepository
from app.repositories.rows import TransactionRow, UserRow
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

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.accounts = AccountRepository(session)
        self.customers = CustomerRepository(session)
        self.transactions = TransactionRepository(session)
        self.otp = OtpService(session)

    async def _customer(self, user_id: int):
        customer = await self.customers.get_by_user_id(user_id)
        if customer is None:
            raise not_found("CUSTOMER_NOT_FOUND", "Customer profile not found")
        if customer.kyc_status != "VERIFIED":
            raise AppError("KYC_NOT_VERIFIED", "Customer KYC must be verified", 403)
        return customer

    async def create(self, user: UserRow, data: TransferRequest) -> tuple[TransactionRow, str]:
        customer = await self._customer(user.id)
        source = await self.accounts.get(data.source_account_id)
        if source is None or source.customer_id != customer.id:
            raise not_found("ACCOUNT_NOT_FOUND", "Source account not found")
        if source.status != "ACTIVE":
            raise AppError("ACCOUNT_LOCKED", "Source account is not active", 409)
        if source.balance < data.amount:
            raise AppError("INSUFFICIENT_BALANCE", "Account balance is insufficient", 409)
        internal = data.bank_code.upper() in self.INTERNAL_BANK_CODES
        destination = await self.accounts.get_by_number(data.destination_account_number) if internal else None
        if internal and destination is None:
            raise not_found("ACCOUNT_NOT_FOUND", "Destination account not found")
        if destination and destination.id == source.id:
            raise AppError("SAME_ACCOUNT_TRANSFER", "Cannot transfer to the same account", 422)
        if destination and (destination.status != "ACTIVE" or destination.currency != source.currency):
            raise AppError("DESTINATION_ACCOUNT_INVALID", "Destination account is not available", 409)
        transaction = await self.transactions.create(
            code=f"TXN-{secrets.token_hex(8).upper()}", kind="INTERNAL_TRANSFER" if internal else "INTERBANK_TRANSFER",
            source_id=source.id, destination_id=destination.id if destination else None,
            destination_number=data.destination_account_number, bank_code=data.bank_code.upper(),
            destination_name=destination.customer_name if destination else None, amount=data.amount,
            currency=source.currency, description=data.description, initiated_by=user.id,
        )
        code = await self.otp.create(user_id=user.id, purpose="TRANSFER", transaction_id=transaction.id)
        await add_audit(
            self.session, user_id=user.id, action="TRANSFER_CREATED", resource_type="transactions",
            resource_id=transaction.id, after={"status": transaction.status, "amount": str(transaction.amount)},
        )
        await self.session.commit()
        return transaction, code

    async def verify_and_execute(self, user: UserRow, transaction_id: int, otp_code: str) -> TransactionRow:
        customer = await self._customer(user.id)
        transaction = await self.transactions.get(transaction_id, lock=True)
        if transaction is None:
            raise not_found("TRANSACTION_NOT_FOUND", "Transaction not found")
        source = await self.accounts.get(transaction.source_account_id) if transaction.source_account_id else None
        if source is None or source.customer_id != customer.id:
            raise forbidden()
        if transaction.status in {"SUCCESS", "FAILED", "CANCELLED"}:
            raise AppError("TRANSACTION_ALREADY_COMPLETED", "Transaction is already completed", 409)
        await self.otp.verify(user_id=user.id, purpose="TRANSFER", code=otp_code, transaction_id=transaction.id)
        account_ids = [source.id]
        if transaction.destination_account_id:
            account_ids.append(transaction.destination_account_id)
        locked = await self.accounts.lock_accounts(account_ids)
        source = locked.get(source.id)
        destination = locked.get(transaction.destination_account_id) if transaction.destination_account_id else None
        if source is None or source.status != "ACTIVE":
            raise AppError("ACCOUNT_LOCKED", "Source account is not active", 409)
        debit_amount = transaction.amount + transaction.fee
        if source.balance < debit_amount:
            raise AppError("INSUFFICIENT_BALANCE", "Account balance is insufficient", 409)
        if transaction.transaction_type == "INTERBANK_TRANSFER":
            result = InterbankGateway().transfer(
                transaction_code=transaction.transaction_code, account_number=transaction.destination_account_number or "",
                bank_code=transaction.destination_bank_code or "", amount=transaction.amount,
            )
            if not result["success"]:
                failed = await self.transactions.set_status(transaction.id, "FAILED", failure_reason="External bank rejected the transfer")
                await add_audit(self.session, user_id=user.id, action="TRANSFER_FAILED", resource_type="transactions", resource_id=transaction.id)
                await self.session.commit()
                return failed
        elif destination is None or destination.status != "ACTIVE":
            raise AppError("DESTINATION_ACCOUNT_INVALID", "Destination account is not active", 409)
        source_before = source.balance
        if not await self.accounts.set_balance(source, source.balance - debit_amount):
            raise AppError("VERSION_CONFLICT", "Source account was modified concurrently", 409)
        await self.accounts.add_entry(transaction.id, source.id, "DEBIT", debit_amount, source_before, source_before - debit_amount)
        if destination:
            destination_before = destination.balance
            if not await self.accounts.set_balance(destination, destination.balance + transaction.amount):
                raise AppError("VERSION_CONFLICT", "Destination account was modified concurrently", 409)
            await self.accounts.add_entry(
                transaction.id, destination.id, "CREDIT", transaction.amount,
                destination_before, destination_before + transaction.amount,
            )
        completed = await self.transactions.set_status(transaction.id, "SUCCESS", completed_at=datetime.now(UTC))
        await add_audit(self.session, user_id=user.id, action="TRANSFER_SUCCESS", resource_type="transactions", resource_id=transaction.id)
        await NotificationService(self.session).create_in_app(
            user.id, "TRANSFER_SUCCESS", "Chuyển khoản thành công", f"Giao dịch {transaction.transaction_code} đã thành công.",
        )
        await self.session.commit()
        return completed

    @staticmethod
    def expose_otp(code: str) -> str | None:
        return code if settings.app_env.lower() == "development" else None
