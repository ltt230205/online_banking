from datetime import UTC, datetime
from decimal import Decimal
import secrets

from sqlalchemy.orm import Session

from app.config import settings
from app.core.exceptions import AppError, forbidden, not_found
from app.models.entities import Payment, Transaction, TransactionEntry, User
from app.repositories.account_repository import AccountRepository
from app.repositories.billing_repository import BillingRepository
from app.repositories.customer_repository import CustomerRepository
from app.services.audit_service import add_audit
from app.services.notification_service import NotificationService
from app.services.otp_service import OtpService


class PaymentService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.customers = CustomerRepository(session)
        self.accounts = AccountRepository(session)
        self.billing = BillingRepository(session)
        self.otp = OtpService(session)

    def _customer(self, user_id: int):
        customer = self.customers.get_by_user_id(user_id)
        if customer is None:
            raise not_found("CUSTOMER_NOT_FOUND", "Customer profile not found")
        if customer.kyc_status != "VERIFIED":
            raise AppError("KYC_NOT_VERIFIED", "Customer KYC must be verified", 403)
        return customer

    def create(self, user: User, invoice_id: int, account_id: int) -> tuple[Payment, str]:
        customer = self._customer(user.id)
        invoice = self.billing.get_invoice(invoice_id)
        if invoice is None or invoice.customer_id != customer.id:
            raise not_found("INVOICE_NOT_FOUND", "Invoice not found")
        if invoice.status == "PAID":
            raise AppError("INVOICE_ALREADY_PAID", "Invoice is already paid", 409)
        if invoice.status != "UNPAID":
            raise AppError("INVOICE_NOT_PAYABLE", "Invoice is not payable", 409)
        account = self.accounts.get(account_id)
        if account is None or account.customer_id != customer.id:
            raise not_found("ACCOUNT_NOT_FOUND", "Account not found")
        if account.status != "ACTIVE":
            raise AppError("ACCOUNT_LOCKED", "Account is not active", 409)
        if account.balance < invoice.amount:
            raise AppError("INSUFFICIENT_BALANCE", "Account balance is insufficient", 409)
        transaction = Transaction(
            transaction_code=f"TXN-{secrets.token_hex(8).upper()}",
            transaction_type="BILL_PAYMENT",
            status="PENDING",
            source_account_id=account.id,
            amount=invoice.amount,
            fee=Decimal("0"),
            currency=invoice.currency,
            description=f"Thanh toán hóa đơn {invoice.invoice_code}",
            initiated_by=user.id,
        )
        self.session.add(transaction)
        self.session.flush()
        payment = Payment(
            payment_code=f"PAY-{secrets.token_hex(8).upper()}",
            invoice_id=invoice.id,
            account_id=account.id,
            transaction_id=transaction.id,
            amount=invoice.amount,
            fee=Decimal("0"),
            status="PENDING",
        )
        self.session.add(payment)
        self.session.flush()
        code = self.otp.create(user_id=user.id, purpose="BILL_PAYMENT", payment_id=payment.id)
        add_audit(self.session, user_id=user.id, action="PAYMENT_CREATED", resource_type="payments", resource_id=payment.id)
        self.session.commit()
        self.session.refresh(payment)
        return payment, code

    def verify_and_execute(self, user: User, payment_id: int, otp_code: str) -> Payment:
        customer = self._customer(user.id)
        payment = self.billing.get_payment(payment_id, lock=True)
        if payment is None:
            raise not_found("PAYMENT_NOT_FOUND", "Payment not found")
        account = self.accounts.get(payment.account_id)
        invoice = self.billing.get_invoice(payment.invoice_id)
        if account is None or invoice is None or account.customer_id != customer.id or invoice.customer_id != customer.id:
            raise forbidden()
        if payment.status in {"SUCCESS", "FAILED", "CANCELLED"}:
            raise AppError("PAYMENT_ALREADY_COMPLETED", "Payment is already completed", 409)
        self.otp.verify(user_id=user.id, purpose="BILL_PAYMENT", code=otp_code, payment_id=payment.id)
        locked_account = self.accounts.lock_accounts([account.id]).get(account.id)
        locked_invoice = self.billing.get_invoice(invoice.id, lock=True)
        if locked_account is None or locked_account.status != "ACTIVE":
            raise AppError("ACCOUNT_LOCKED", "Account is not active", 409)
        if locked_invoice is None or locked_invoice.status == "PAID":
            raise AppError("INVOICE_ALREADY_PAID", "Invoice is already paid", 409)
        if locked_invoice.status != "UNPAID":
            raise AppError("INVOICE_NOT_PAYABLE", "Invoice is not payable", 409)
        debit = payment.amount + payment.fee
        if locked_account.balance < debit:
            raise AppError("INSUFFICIENT_BALANCE", "Account balance is insufficient", 409)
        before = locked_account.balance
        locked_account.balance -= debit
        locked_account.version += 1
        self.session.add(
            TransactionEntry(
                transaction_id=payment.transaction_id,
                account_id=locked_account.id,
                entry_type="DEBIT",
                amount=debit,
                balance_before=before,
                balance_after=locked_account.balance,
            )
        )
        transaction = self.session.get(Transaction, payment.transaction_id)
        transaction.status = "SUCCESS"
        transaction.completed_at = datetime.now(UTC)
        payment.status = "SUCCESS"
        payment.completed_at = datetime.now(UTC)
        locked_invoice.status = "PAID"
        locked_invoice.paid_at = datetime.now(UTC)
        locked_invoice.version += 1
        add_audit(self.session, user_id=user.id, action="PAYMENT_SUCCESS", resource_type="payments", resource_id=payment.id)
        NotificationService(self.session).create_in_app(
            user.id, "PAYMENT_SUCCESS", "Thanh toán thành công", f"Hóa đơn {locked_invoice.invoice_code} đã được thanh toán."
        )
        self.session.commit()
        self.session.refresh(payment)
        return payment

    @staticmethod
    def expose_otp(code: str) -> str | None:
        return code if settings.app_env.lower() == "development" else None
