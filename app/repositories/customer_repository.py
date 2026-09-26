from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.entities import Customer


class CustomerRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_user_id(self, user_id: int) -> Customer | None:
        return self.session.scalar(
            select(Customer).where(Customer.user_id == user_id, Customer.is_deleted.is_(False))
        )

    def get(self, customer_id: int) -> Customer | None:
        return self.session.scalar(
            select(Customer).where(Customer.id == customer_id, Customer.is_deleted.is_(False))
        )

    def identity_exists(self, identity_number: str) -> bool:
        return bool(self.session.scalar(select(func.count()).select_from(Customer).where(Customer.identity_number == identity_number)))

    def next_code(self) -> str:
        next_id = int(self.session.scalar(select(func.coalesce(func.max(Customer.id), 0))) or 0) + 1
        return f"CUS{next_id:06d}"

    def list(self, offset: int, limit: int, kyc_status: str | None = None) -> list[Customer]:
        query = select(Customer).where(Customer.is_deleted.is_(False))
        if kyc_status:
            query = query.where(Customer.kyc_status == kyc_status)
        return list(self.session.scalars(query.order_by(Customer.id).offset(offset).limit(limit)))
