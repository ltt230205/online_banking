from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.db import execute, query, query_one, scalar, where
from app.repositories.rows import TransactionRow


class TransactionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, transaction_id: int, *, lock: bool = False) -> TransactionRow | None:
        sql = "SELECT * FROM transactions WHERE id=:id" + (" FOR UPDATE" if lock else "")
        return await query_one(self.session, sql, {"id": transaction_id}, TransactionRow)

    async def create(self, *, code: str, kind: str, source_id: int, destination_id: int | None, destination_number: str | None,
                     bank_code: str | None, destination_name: str | None, amount: Decimal, currency: str,
                     description: str | None, initiated_by: int) -> TransactionRow:
        transaction_id = await scalar(
            self.session,
            "INSERT INTO transactions(transaction_code, transaction_type, status, source_account_id, destination_account_id, "
            "destination_account_number, destination_bank_code, destination_account_name, amount, fee, currency, description, initiated_by) "
            "VALUES (:code, :kind, 'PENDING', :source, :destination, :number, :bank_code, :name, :amount, 0, :currency, :description, :user) RETURNING id",
            {"code": code, "kind": kind, "source": source_id, "destination": destination_id, "number": destination_number,
             "bank_code": bank_code, "name": destination_name, "amount": amount, "currency": currency,
             "description": description, "user": initiated_by},
        )
        return await self.get(transaction_id)

    async def set_status(self, transaction_id: int, status: str, completed_at: datetime | None = None, failure_reason: str | None = None) -> TransactionRow:
        await execute(
            self.session,
            "UPDATE transactions SET status=:status, completed_at=:completed_at, failure_reason=:failure_reason WHERE id=:id",
            {"id": transaction_id, "status": status, "completed_at": completed_at, "failure_reason": failure_reason},
        )
        return await self.get(transaction_id)

    async def list(self, *, customer_id: int | None, page: int, page_size: int, transaction_type: str | None,
                   status: str | None, from_date: datetime | None, to_date: datetime | None) -> tuple[list[TransactionRow], int]:
        clause, params = where({"transaction_type": transaction_type, "status": status},
                               {"transaction_type": "t.transaction_type", "status": "t.status"})
        predicates: list[str] = []
        if clause:
            predicates.append(clause.removeprefix(" WHERE "))
        if customer_id is not None:
            predicates.append("(t.source_account_id IN (SELECT id FROM accounts WHERE customer_id=:customer_id) OR "
                              "t.destination_account_id IN (SELECT id FROM accounts WHERE customer_id=:customer_id))")
            params["customer_id"] = customer_id
        if from_date is not None:
            predicates.append("t.created_at>=:from_date")
            params["from_date"] = from_date
        if to_date is not None:
            predicates.append("t.created_at<=:to_date")
            params["to_date"] = to_date
        conditions = " WHERE " + " AND ".join(predicates) if predicates else ""
        total = int(await scalar(self.session, "SELECT COUNT(*) FROM transactions t" + conditions, params) or 0)
        items = await query(
            self.session, "SELECT t.* FROM transactions t" + conditions + " ORDER BY t.created_at DESC, t.id DESC OFFSET :offset LIMIT :limit",
            {**params, "offset": (page - 1) * page_size, "limit": page_size}, TransactionRow,
        )
        return items, total
