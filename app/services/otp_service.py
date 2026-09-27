from datetime import UTC, datetime, timedelta
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.core.security import generate_otp, hash_otp, verify_otp_hash
from app.models.entities import OtpCode


logger = logging.getLogger(__name__)


class OtpService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        *,
        user_id: int,
        purpose: str,
        transaction_id: int | None = None,
        payment_id: int | None = None,
    ) -> str:
        code = generate_otp()
        self.session.add(
            OtpCode(
                user_id=user_id,
                purpose=purpose,
                code_hash=hash_otp(code),
                transaction_id=transaction_id,
                payment_id=payment_id,
                expires_at=datetime.now(UTC) + timedelta(minutes=5),
                max_attempts=5,
            )
        )
        logger.info("Development OTP generated for user_id=%s purpose=%s: %s", user_id, purpose, code)
        return code

    def verify(
        self,
        *,
        user_id: int,
        purpose: str,
        code: str,
        transaction_id: int | None = None,
        payment_id: int | None = None,
    ) -> OtpCode:
        query = select(OtpCode).where(
            OtpCode.user_id == user_id,
            OtpCode.purpose == purpose,
            OtpCode.consumed_at.is_(None),
        )
        query = query.where(
            OtpCode.transaction_id == transaction_id if transaction_id is not None else OtpCode.transaction_id.is_(None),
            OtpCode.payment_id == payment_id if payment_id is not None else OtpCode.payment_id.is_(None),
        )
        otp = self.session.scalar(query.order_by(OtpCode.created_at.desc()).with_for_update())
        if otp is None:
            raise AppError("INVALID_OTP", "OTP is invalid", 400)
        now = datetime.now(UTC)
        if otp.expires_at <= now:
            raise AppError("OTP_EXPIRED", "OTP has expired", 400)
        if otp.failed_attempts >= otp.max_attempts:
            raise AppError("INVALID_OTP", "OTP attempt limit exceeded", 400)
        if not verify_otp_hash(code, otp.code_hash):
            otp.failed_attempts += 1
            self.session.commit()
            raise AppError("INVALID_OTP", "OTP is invalid", 400)
        otp.consumed_at = now
        return otp
