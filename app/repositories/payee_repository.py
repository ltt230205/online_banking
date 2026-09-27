from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.db import execute, query, query_one, scalar
from app.repositories.rows import PayeeRow


class PayeeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(self, customer_id: int) -> list[PayeeRow]:
        return await query(self.session, "SELECT * FROM payees WHERE customer_id=:id AND is_deleted=false ORDER BY id", {"id": customer_id}, PayeeRow)

    async def get(self, payee_id: int) -> PayeeRow | None:
        return await query_one(self.session, "SELECT * FROM payees WHERE id=:id AND is_deleted=false", {"id": payee_id}, PayeeRow)

    async def create(self, customer_id: int, nickname: str, number: str, name: str, bank_code: str, linked_account_id: int | None) -> PayeeRow:
        payee_id = await scalar(
            self.session,
            "INSERT INTO payees(customer_id, nickname, account_number, account_name, bank_code, is_internal, linked_account_id) "
            "VALUES (:customer_id, :nickname, :number, :name, :bank_code, :internal, :linked) RETURNING id",
            {"customer_id": customer_id, "nickname": nickname, "number": number, "name": name, "bank_code": bank_code,
             "internal": linked_account_id is not None, "linked": linked_account_id},
        )
        return await self.get(payee_id)

    async def soft_delete(self, payee_id: int, actor_id: int, at: datetime) -> None:
        await execute(self.session, "UPDATE payees SET is_deleted=true, deleted_at=:at, deleted_by=:actor, updated_at=now() WHERE id=:id", {"id": payee_id, "actor": actor_id, "at": at})
