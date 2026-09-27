from datetime import date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.db import execute, query, query_one, scalar, update_versioned, where
from app.repositories.rows import CustomerRow


class CustomerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_user_id(self, user_id: int) -> CustomerRow | None:
        return await query_one(self.session, "SELECT * FROM customers WHERE user_id=:user_id AND is_deleted=false", {"user_id": user_id}, CustomerRow)

    async def get(self, customer_id: int) -> CustomerRow | None:
        return await query_one(self.session, "SELECT * FROM customers WHERE id=:id AND is_deleted=false", {"id": customer_id}, CustomerRow)

    async def identity_exists(self, identity_number: str) -> bool:
        return bool(await scalar(self.session, "SELECT EXISTS(SELECT 1 FROM customers WHERE identity_number=:identity)", {"identity": identity_number}))

    async def next_code(self) -> str:
        next_id = int(await scalar(self.session, "SELECT COALESCE(MAX(id), 0) + 1 FROM customers") or 1)
        return f"CUS{next_id:06d}"

    async def create(self, user_id: int, code: str, name: str, dob: date, identity: str, phone: str, address: str | None) -> CustomerRow:
        customer_id = await scalar(
            self.session,
            "INSERT INTO customers(user_id, customer_code, full_name, date_of_birth, identity_number, phone, address, kyc_status) "
            "VALUES (:user_id, :code, :name, :dob, :identity, :phone, :address, 'PENDING') RETURNING id",
            {"user_id": user_id, "code": code, "name": name, "dob": dob, "identity": identity, "phone": phone, "address": address},
        )
        await execute(self.session, "INSERT INTO kyc_requests(customer_id, status, document_data) VALUES (:id, 'PENDING', '{}'::jsonb)", {"id": customer_id})
        return await self.get(customer_id)

    async def list(self, offset: int, limit: int, kyc_status: str | None = None) -> list[CustomerRow]:
        clause, params = where({"kyc_status": kyc_status}, {"kyc_status": "kyc_status"})
        sql = "SELECT * FROM customers WHERE is_deleted=false" + clause.replace(" WHERE ", " AND ") + " ORDER BY id OFFSET :offset LIMIT :limit"
        return await query(self.session, sql, {**params, "offset": offset, "limit": limit}, CustomerRow)

    async def update_kyc(self, customer: CustomerRow, status: str, verified_at: datetime | None) -> CustomerRow | None:
        version = await update_versioned(self.session, "customers", customer.id, customer.version, {"kyc_status": status, "kyc_verified_at": verified_at})
        return await self.get(customer.id) if version is not None else None

    async def close_pending_kyc(self, customer_id: int, status: str, actor_id: int, reason: str | None) -> None:
        await execute(
            self.session,
            "UPDATE kyc_requests SET status=:status, reviewed_by=:actor_id, reviewed_at=now(), rejection_reason=:reason "
            "WHERE id=(SELECT id FROM kyc_requests WHERE customer_id=:customer_id AND status='PENDING' "
            "ORDER BY submitted_at DESC LIMIT 1 FOR UPDATE)",
            {"status": status, "actor_id": actor_id, "reason": reason, "customer_id": customer_id},
        )
