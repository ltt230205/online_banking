from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.db import execute, query, query_one, update_versioned
from app.repositories.rows import AccountRow, StatementRow


ACCOUNT_SQL = "SELECT a.*, c.full_name AS customer_name FROM accounts a JOIN customers c ON c.id=a.customer_id"


class AccountRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_customer(self, customer_id: int) -> list[AccountRow]:
        return await query(self.session, ACCOUNT_SQL + " WHERE a.customer_id=:id AND a.is_deleted=false ORDER BY a.id", {"id": customer_id}, AccountRow)

    async def list_all(self, offset: int, limit: int) -> list[AccountRow]:
        return await query(self.session, ACCOUNT_SQL + " WHERE a.is_deleted=false ORDER BY a.id OFFSET :offset LIMIT :limit", {"offset": offset, "limit": limit}, AccountRow)

    async def get(self, account_id: int) -> AccountRow | None:
        return await query_one(self.session, ACCOUNT_SQL + " WHERE a.id=:id AND a.is_deleted=false", {"id": account_id}, AccountRow)

    async def get_by_number(self, number: str) -> AccountRow | None:
        return await query_one(self.session, ACCOUNT_SQL + " WHERE a.account_number=:number AND a.is_deleted=false", {"number": number}, AccountRow)

    async def lock_accounts(self, account_ids: list[int]) -> dict[int, AccountRow]:
        rows = await query(
            self.session,
            ACCOUNT_SQL + " WHERE a.id = ANY(:ids) AND a.is_deleted=false ORDER BY a.id FOR UPDATE OF a",
            {"ids": sorted(set(account_ids))}, AccountRow,
        )
        return {row.id: row for row in rows}

    async def set_balance(self, account: AccountRow, balance: Decimal) -> bool:
        return await update_versioned(self.session, "accounts", account.id, account.version, {"balance": balance}) is not None

    async def add_entry(self, transaction_id: int, account_id: int, entry_type: str, amount: Decimal, before: Decimal, after: Decimal) -> None:
        await execute(
            self.session,
            "INSERT INTO transaction_entries(transaction_id, account_id, entry_type, amount, balance_before, balance_after) "
            "VALUES (:tx, :account, :kind, :amount, :before, :after)",
            {"tx": transaction_id, "account": account_id, "kind": entry_type, "amount": amount, "before": before, "after": after},
        )

    async def statement_rows(self, account_id: int, from_date: datetime, to_date: datetime) -> list[StatementRow]:
        return await query(
            self.session,
            "SELECT e.created_at, t.transaction_code, t.description, e.entry_type, e.amount, e.balance_before, e.balance_after "
            "FROM transaction_entries e JOIN transactions t ON t.id=e.transaction_id "
            "WHERE e.account_id=:id AND e.created_at>=:from_date AND e.created_at<=:to_date AND t.status='SUCCESS' "
            "ORDER BY e.created_at, e.id",
            {"id": account_id, "from_date": from_date, "to_date": to_date}, StatementRow,
        )

    async def previous_entry(self, account_id: int, from_date: datetime) -> StatementRow | None:
        return await query_one(
            self.session,
            "SELECT e.created_at, t.transaction_code, t.description, e.entry_type, e.amount, e.balance_before, e.balance_after "
            "FROM transaction_entries e JOIN transactions t ON t.id=e.transaction_id "
            "WHERE e.account_id=:id AND e.created_at<:from_date AND t.status='SUCCESS' "
            "ORDER BY e.created_at DESC, e.id DESC LIMIT 1",
            {"id": account_id, "from_date": from_date}, StatementRow,
        )
