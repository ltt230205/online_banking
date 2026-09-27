from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import forbidden, not_found
from app.repositories.account_repository import AccountRepository
from app.repositories.customer_repository import CustomerRepository
from app.repositories.rows import AccountRow, UserRow
from app.schemas.account import StatementEntry, StatementResponse


class AccountService:
    def __init__(self, session: AsyncSession) -> None:
        self.accounts = AccountRepository(session)
        self.customers = CustomerRepository(session)

    async def customer_for_user(self, user_id: int):
        customer = await self.customers.get_by_user_id(user_id)
        if customer is None:
            raise not_found("CUSTOMER_NOT_FOUND", "Customer profile not found")
        return customer

    async def list_for_user(self, user_id: int) -> list[AccountRow]:
        return await self.accounts.list_for_customer((await self.customer_for_user(user_id)).id)

    async def get_authorized(self, account_id: int, user: UserRow) -> AccountRow:
        account = await self.accounts.get(account_id)
        if account is None:
            raise not_found("ACCOUNT_NOT_FOUND", "Account not found")
        if user.role_name == "CUSTOMER":
            customer = await self.customer_for_user(user.id)
            if account.customer_id != customer.id:
                raise forbidden()
        return account

    async def statement(self, account_id: int, user: UserRow, from_date: datetime, to_date: datetime) -> StatementResponse:
        if from_date >= to_date:
            raise ValueError("from_date must be before to_date")
        account = await self.get_authorized(account_id, user)
        rows = await self.accounts.statement_rows(account.id, from_date, to_date)
        if rows:
            opening = rows[0].balance_before
            closing = rows[-1].balance_after
        else:
            previous = await self.accounts.previous_entry(account.id, from_date)
            opening = previous.balance_after if previous else account.balance
            closing = opening
        entries = [
            StatementEntry(
                date=row.created_at, transaction_code=row.transaction_code, description=row.description,
                debit=row.amount if row.entry_type == "DEBIT" else Decimal("0"),
                credit=row.amount if row.entry_type == "CREDIT" else Decimal("0"), balance=row.balance_after,
            ) for row in rows
        ]
        return StatementResponse(
            account_number=account.account_number, customer_name=account.customer_name or "",
            from_date=from_date.astimezone(UTC), to_date=to_date.astimezone(UTC),
            opening_balance=opening, closing_balance=closing, transactions=entries,
        )
