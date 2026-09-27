from datetime import UTC, datetime, timedelta
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.core.security import generate_otp, hash_otp, verify_otp_hash
from app.repositories.otp_repository import OtpRepository
from app.repositories.rows import OtpRow


logger = logging.getLogger(__name__)


class OtpService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.otps = OtpRepository(session)

    async def create(self, *, user_id: int, purpose: str, transaction_id: int | None = None, payment_id: int | None = None) -> str:
        code = generate_otp()
        await self.otps.create(
            user_id=user_id, purpose=purpose, code_hash=hash_otp(code),
            transaction_id=transaction_id, payment_id=payment_id, expires_at=datetime.now(UTC) + timedelta(minutes=5),
        )
        logger.info("Development OTP generated for user_id=%s purpose=%s: %s", user_id, purpose, code)
        return code

    async def verify(self, *, user_id: int, purpose: str, code: str,
                     transaction_id: int | None = None, payment_id: int | None = None) -> OtpRow:
        otp = await self.otps.latest_unconsumed(
            user_id=user_id, purpose=purpose, transaction_id=transaction_id, payment_id=payment_id,
        )
        if otp is None:
            raise AppError("INVALID_OTP", "OTP is invalid", 400)
        now = datetime.now(UTC)
        if otp.expires_at <= now:
            raise AppError("OTP_EXPIRED", "OTP has expired", 400)
        if otp.failed_attempts >= otp.max_attempts:
            raise AppError("INVALID_OTP", "OTP attempt limit exceeded", 400)
        if not verify_otp_hash(code, otp.code_hash):
            await self.otps.increment_failed(otp.id)
            await self.session.commit()
            raise AppError("INVALID_OTP", "OTP is invalid", 400)
        await self.otps.consume(otp.id, now)
        return otp
