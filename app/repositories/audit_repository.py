import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.db import execute, query
from app.repositories.rows import AuditRow


class AuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, *, user_id: int | None, action: str, resource_type: str, resource_id: int | str | None,
                     before: dict | None, after: dict | None) -> None:
        await execute(
            self.session,
            "INSERT INTO audit_logs(user_id, action, resource_type, resource_id, before_data, after_data) "
            "VALUES (:user_id, :action, :resource_type, :resource_id, CAST(:before AS jsonb), CAST(:after AS jsonb))",
            {"user_id": user_id, "action": action, "resource_type": resource_type,
             "resource_id": str(resource_id) if resource_id is not None else None,
             "before": json.dumps(before) if before is not None else None,
             "after": json.dumps(after) if after is not None else None},
        )

    async def list(self, offset: int, limit: int) -> list[AuditRow]:
        return await query(
            self.session,
            "SELECT id, user_id, action, resource_type, resource_id, created_at FROM audit_logs "
            "ORDER BY created_at DESC OFFSET :offset LIMIT :limit",
            {"offset": offset, "limit": limit}, AuditRow,
        )
