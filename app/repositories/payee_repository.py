from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Payee


class PayeeRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self, customer_id: int) -> list[Payee]:
        return list(
            self.session.scalars(
                select(Payee).where(Payee.customer_id == customer_id, Payee.is_deleted.is_(False)).order_by(Payee.id)
            )
        )

    def get(self, payee_id: int) -> Payee | None:
        return self.session.scalar(select(Payee).where(Payee.id == payee_id, Payee.is_deleted.is_(False)))
