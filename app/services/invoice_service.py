from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import forbidden, not_found
from app.repositories.billing_repository import BillingRepository
from app.repositories.customer_repository import CustomerRepository
from app.repositories.rows import InvoiceRow, UserRow


class InvoiceService:
    def __init__(self, session: AsyncSession) -> None:
        self.customers = CustomerRepository(session)
        self.billing = BillingRepository(session)

    async def _customer(self, user_id: int):
        customer = await self.customers.get_by_user_id(user_id)
        if customer is None:
            raise not_found("CUSTOMER_NOT_FOUND", "Customer profile not found")
        return customer

    async def list(self, user: UserRow) -> list[InvoiceRow]:
        return await self.billing.list_invoices((await self._customer(user.id)).id)

    async def get(self, user: UserRow, invoice_id: int) -> InvoiceRow:
        customer = await self._customer(user.id)
        invoice = await self.billing.get_invoice(invoice_id)
        if invoice is None:
            raise not_found("INVOICE_NOT_FOUND", "Invoice not found")
        if invoice.customer_id != customer.id:
            raise forbidden()
        return invoice
