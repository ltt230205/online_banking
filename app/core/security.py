from datetime import UTC, datetime, timedelta
import hashlib
import hmac
import secrets

import jwt
from pwdlib import PasswordHash

from app.config import settings


password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)


def create_access_token(*, user_id: int, username: str, role: str) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "user_id": user_id,
        "username": username,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> dict[str, object]:
    return jwt.decode(
        token,
        settings.jwt_secret_key.get_secret_value(),
        algorithms=[settings.jwt_algorithm],
    )


def generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp(otp: str) -> str:
    return hmac.new(
        settings.jwt_secret_key.get_secret_value().encode(),
        otp.encode(),
        hashlib.sha256,
    ).hexdigest()


def verify_otp_hash(otp: str, expected_hash: str) -> bool:
    return hmac.compare_digest(hash_otp(otp), expected_hash)
