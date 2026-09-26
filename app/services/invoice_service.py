from sqlalchemy.orm import Session

from app.core.exceptions import forbidden, not_found
from app.models.entities import User
from app.repositories.billing_repository import BillingRepository
from app.repositories.customer_repository import CustomerRepository


class InvoiceService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.customers = CustomerRepository(session)
        self.billing = BillingRepository(session)

    def _customer(self, user_id: int):
        customer = self.customers.get_by_user_id(user_id)
        if customer is None:
            raise not_found("CUSTOMER_NOT_FOUND", "Customer profile not found")
        return customer

    def list(self, user: User):
        return self.billing.list_invoices(self._customer(user.id).id)

    def get(self, user: User, invoice_id: int):
        customer = self._customer(user.id)
        invoice = self.billing.get_invoice(invoice_id)
        if invoice is None:
            raise not_found("INVOICE_NOT_FOUND", "Invoice not found")
        if invoice.customer_id != customer.id:
            raise forbidden()
        return invoice
