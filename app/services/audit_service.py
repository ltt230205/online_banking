from typing import Any

from sqlalchemy.orm import Session

from app.models.entities import AuditLog


SENSITIVE_KEYS = {"password", "password_hash", "token", "access_token", "refresh_token", "otp", "code_hash"}


def _redact(data: dict[str, Any] | None) -> dict[str, Any] | None:
    if data is None:
        return None
    return {key: "[REDACTED]" if key.lower() in SENSITIVE_KEYS else value for key, value in data.items()}


def add_audit(
    session: Session,
    *,
    user_id: int | None,
    action: str,
    resource_type: str,
    resource_id: int | str | None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
) -> None:
    session.add(
        AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id is not None else None,
            before_data=_redact(before),
            after_data=_redact(after),
        )
    )
