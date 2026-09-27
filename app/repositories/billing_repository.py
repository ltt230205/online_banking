from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Invoice, Payment


class BillingRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_invoices(self, customer_id: int) -> list[Invoice]:
        return list(
            self.session.scalars(
                select(Invoice).where(Invoice.customer_id == customer_id, Invoice.is_deleted.is_(False)).order_by(Invoice.due_date)
            )
        )

    def get_invoice(self, invoice_id: int, *, lock: bool = False) -> Invoice | None:
        query = select(Invoice).where(Invoice.id == invoice_id, Invoice.is_deleted.is_(False))
        if lock:
            query = query.with_for_update()
        return self.session.scalar(query)

    def get_payment(self, payment_id: int, *, lock: bool = False) -> Payment | None:
        query = select(Payment).where(Payment.id == payment_id)
        if lock:
            query = query.with_for_update()
        return self.session.scalar(query)
