from datetime import datetime

from sqlalchemy.orm import Session

from app.core.exceptions import not_found
from app.models.entities import User
from app.repositories.customer_repository import CustomerRepository
from app.repositories.transaction_repository import TransactionRepository


class TransactionService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.customers = CustomerRepository(session)
        self.transactions = TransactionRepository(session)

    def list(
        self,
        *,
        user: User,
        page: int,
        page_size: int,
        transaction_type: str | None,
        status: str | None,
        from_date: datetime | None,
        to_date: datetime | None,
    ):
        customer_id = None
        if user.role.name == "CUSTOMER":
            customer = self.customers.get_by_user_id(user.id)
            if customer is None:
                raise not_found("CUSTOMER_NOT_FOUND", "Customer profile not found")
            customer_id = customer.id
        return self.transactions.list(
            customer_id=customer_id,
            page=page,
            page_size=page_size,
            transaction_type=transaction_type,
            status=status,
            from_date=from_date,
            to_date=to_date,
        )
