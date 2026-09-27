from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.db import execute, query, query_one, scalar, update_versioned
from app.repositories.rows import InvoiceRow, PaymentRow


class BillingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_invoices(self, customer_id: int) -> list[InvoiceRow]:
        return await query(self.session, "SELECT * FROM invoices WHERE customer_id=:id AND is_deleted=false ORDER BY due_date", {"id": customer_id}, InvoiceRow)

    async def get_invoice(self, invoice_id: int, *, lock: bool = False) -> InvoiceRow | None:
        sql = "SELECT * FROM invoices WHERE id=:id AND is_deleted=false" + (" FOR UPDATE" if lock else "")
        return await query_one(self.session, sql, {"id": invoice_id}, InvoiceRow)

    async def get_payment(self, payment_id: int, *, lock: bool = False) -> PaymentRow | None:
        sql = "SELECT * FROM payments WHERE id=:id" + (" FOR UPDATE" if lock else "")
        return await query_one(self.session, sql, {"id": payment_id}, PaymentRow)

    async def create_payment(self, invoice_id: int, account_id: int, transaction_id: int, amount: Decimal, code: str) -> PaymentRow:
        payment_id = await scalar(
            self.session,
            "INSERT INTO payments(payment_code, invoice_id, account_id, transaction_id, amount, fee, status) "
            "VALUES (:code, :invoice_id, :account_id, :tx, :amount, 0, 'PENDING') RETURNING id",
            {"code": code, "invoice_id": invoice_id, "account_id": account_id, "tx": transaction_id, "amount": amount},
        )
        return await self.get_payment(payment_id)

    async def complete_payment(self, payment_id: int, at: datetime) -> PaymentRow:
        await execute(self.session, "UPDATE payments SET status='SUCCESS', completed_at=:at WHERE id=:id", {"id": payment_id, "at": at})
        return await self.get_payment(payment_id)

    async def mark_invoice_paid(self, invoice: InvoiceRow, at: datetime) -> bool:
        return await update_versioned(self.session, "invoices", invoice.id, invoice.version, {"status": "PAID", "paid_at": at}) is not None
