from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.db import execute, query_one
from app.repositories.rows import OtpRow


class OtpRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, *, user_id: int, purpose: str, code_hash: str, expires_at: datetime,
                     transaction_id: int | None, payment_id: int | None) -> None:
        await execute(
            self.session,
            "INSERT INTO otp_codes(user_id, purpose, code_hash, expires_at, transaction_id, payment_id) "
            "VALUES (:user_id, :purpose, :hash, :expires, :transaction_id, :payment_id)",
            {"user_id": user_id, "purpose": purpose, "hash": code_hash, "expires": expires_at,
             "transaction_id": transaction_id, "payment_id": payment_id},
        )

    async def latest_unconsumed(self, *, user_id: int, purpose: str, transaction_id: int | None, payment_id: int | None) -> OtpRow | None:
        return await query_one(
            self.session,
            "SELECT * FROM otp_codes WHERE user_id=:user_id AND purpose=:purpose AND consumed_at IS NULL "
            "AND transaction_id IS NOT DISTINCT FROM :transaction_id "
            "AND payment_id IS NOT DISTINCT FROM :payment_id ORDER BY created_at DESC LIMIT 1 FOR UPDATE",
            {"user_id": user_id, "purpose": purpose, "transaction_id": transaction_id, "payment_id": payment_id}, OtpRow,
        )

    async def increment_failed(self, otp_id: int) -> None:
        await execute(self.session, "UPDATE otp_codes SET failed_attempts=failed_attempts+1 WHERE id=:id", {"id": otp_id})

    async def consume(self, otp_id: int, at: datetime) -> None:
        await execute(self.session, "UPDATE otp_codes SET consumed_at=:at WHERE id=:id", {"id": otp_id, "at": at})
