from datetime import UTC, datetime
from decimal import Decimal
import secrets

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import AppError, forbidden, not_found
from app.repositories.account_repository import AccountRepository
from app.repositories.billing_repository import BillingRepository
from app.repositories.customer_repository import CustomerRepository
from app.repositories.rows import PaymentRow, UserRow
from app.repositories.transaction_repository import TransactionRepository
from app.services.audit_service import add_audit
from app.services.notification_service import NotificationService
from app.services.otp_service import OtpService


class PaymentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.customers = CustomerRepository(session)
        self.accounts = AccountRepository(session)
        self.billing = BillingRepository(session)
        self.transactions = TransactionRepository(session)
        self.otp = OtpService(session)

    async def _customer(self, user_id: int):
        customer = await self.customers.get_by_user_id(user_id)
        if customer is None:
            raise not_found("CUSTOMER_NOT_FOUND", "Customer profile not found")
        if customer.kyc_status != "VERIFIED":
            raise AppError("KYC_NOT_VERIFIED", "Customer KYC must be verified", 403)
        return customer

    async def create(self, user: UserRow, invoice_id: int, account_id: int) -> tuple[PaymentRow, str]:
        customer = await self._customer(user.id)
        invoice = await self.billing.get_invoice(invoice_id)
        if invoice is None or invoice.customer_id != customer.id:
            raise not_found("INVOICE_NOT_FOUND", "Invoice not found")
        if invoice.status == "PAID":
            raise AppError("INVOICE_ALREADY_PAID", "Invoice is already paid", 409)
        if invoice.status != "UNPAID":
            raise AppError("INVOICE_NOT_PAYABLE", "Invoice is not payable", 409)
        account = await self.accounts.get(account_id)
        if account is None or account.customer_id != customer.id:
            raise not_found("ACCOUNT_NOT_FOUND", "Account not found")
        if account.status != "ACTIVE":
            raise AppError("ACCOUNT_LOCKED", "Account is not active", 409)
        if account.balance < invoice.amount:
            raise AppError("INSUFFICIENT_BALANCE", "Account balance is insufficient", 409)
        transaction = await self.transactions.create(
            code=f"TXN-{secrets.token_hex(8).upper()}", kind="BILL_PAYMENT", source_id=account.id,
            destination_id=None, destination_number=None, bank_code=None, destination_name=None,
            amount=invoice.amount, currency=invoice.currency, description=f"Thanh toán hóa đơn {invoice.invoice_code}",
            initiated_by=user.id,
        )
        payment = await self.billing.create_payment(
            invoice.id, account.id, transaction.id, invoice.amount, f"PAY-{secrets.token_hex(8).upper()}",
        )
        code = await self.otp.create(user_id=user.id, purpose="BILL_PAYMENT", payment_id=payment.id)
        await add_audit(self.session, user_id=user.id, action="PAYMENT_CREATED", resource_type="payments", resource_id=payment.id)
        await self.session.commit()
        return payment, code

    async def verify_and_execute(self, user: UserRow, payment_id: int, otp_code: str) -> PaymentRow:
        customer = await self._customer(user.id)
        payment = await self.billing.get_payment(payment_id, lock=True)
        if payment is None:
            raise not_found("PAYMENT_NOT_FOUND", "Payment not found")
        account = await self.accounts.get(payment.account_id)
        invoice = await self.billing.get_invoice(payment.invoice_id)
        if account is None or invoice is None or account.customer_id != customer.id or invoice.customer_id != customer.id:
            raise forbidden()
        if payment.status in {"SUCCESS", "FAILED", "CANCELLED"}:
            raise AppError("PAYMENT_ALREADY_COMPLETED", "Payment is already completed", 409)
        await self.otp.verify(user_id=user.id, purpose="BILL_PAYMENT", code=otp_code, payment_id=payment.id)
        locked_account = (await self.accounts.lock_accounts([account.id])).get(account.id)
        locked_invoice = await self.billing.get_invoice(invoice.id, lock=True)
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
        if not await self.accounts.set_balance(locked_account, before - debit):
            raise AppError("VERSION_CONFLICT", "Account was modified concurrently", 409)
        await self.accounts.add_entry(payment.transaction_id, locked_account.id, "DEBIT", debit, before, before - debit)
        now = datetime.now(UTC)
        await self.transactions.set_status(payment.transaction_id, "SUCCESS", completed_at=now)
        completed = await self.billing.complete_payment(payment.id, now)
        if not await self.billing.mark_invoice_paid(locked_invoice, now):
            raise AppError("VERSION_CONFLICT", "Invoice was modified concurrently", 409)
        await add_audit(self.session, user_id=user.id, action="PAYMENT_SUCCESS", resource_type="payments", resource_id=payment.id)
        await NotificationService(self.session).create_in_app(
            user.id, "PAYMENT_SUCCESS", "Thanh toán thành công", f"Hóa đơn {locked_invoice.invoice_code} đã được thanh toán.",
        )
        await self.session.commit()
        return completed

    @staticmethod
    def expose_otp(code: str) -> str | None:
        return code if settings.app_env.lower() == "development" else None
