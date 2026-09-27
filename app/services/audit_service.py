from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.audit_repository import AuditRepository


SENSITIVE_KEYS = {"password", "password_hash", "token", "access_token", "refresh_token", "otp", "code_hash"}


def _redact(data: dict[str, Any] | None) -> dict[str, Any] | None:
    if data is None:
        return None
    return {key: "[REDACTED]" if key.lower() in SENSITIVE_KEYS else value for key, value in data.items()}


async def add_audit(
    session: AsyncSession,
    *,
    user_id: int | None,
    action: str,
    resource_type: str,
    resource_id: int | str | None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
) -> None:
    await AuditRepository(session).create(
        user_id=user_id, action=action, resource_type=resource_type, resource_id=resource_id,
        before=_redact(before), after=_redact(after),
    )
