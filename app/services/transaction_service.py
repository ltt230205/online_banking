from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import not_found
from app.repositories.customer_repository import CustomerRepository
from app.repositories.rows import UserRow
from app.repositories.transaction_repository import TransactionRepository


class TransactionService:
    def __init__(self, session: AsyncSession) -> None:
        self.customers = CustomerRepository(session)
        self.transactions = TransactionRepository(session)

    async def list(self, *, user: UserRow, page: int, page_size: int, transaction_type: str | None,
                   status: str | None, from_date: datetime | None, to_date: datetime | None):
        customer_id = None
        if user.role_name == "CUSTOMER":
            customer = await self.customers.get_by_user_id(user.id)
            if customer is None:
                raise not_found("CUSTOMER_NOT_FOUND", "Customer profile not found")
            customer_id = customer.id
        return await self.transactions.list(
            customer_id=customer_id, page=page, page_size=page_size, transaction_type=transaction_type,
            status=status, from_date=from_date, to_date=to_date,
        )
