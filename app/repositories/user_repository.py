from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.db import query, query_one, scalar, execute
from app.repositories.rows import RoleRow, UserRow


USER_SQL = "SELECT u.*, r.name AS role_name FROM users u JOIN roles r ON r.id = u.role_id"


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, user_id: int) -> UserRow | None:
        return await query_one(self.session, USER_SQL + " WHERE u.id=:id AND u.is_deleted=false", {"id": user_id}, UserRow)

    async def get_by_username(self, username: str) -> UserRow | None:
        return await query_one(self.session, USER_SQL + " WHERE u.username=:username AND u.is_deleted=false", {"username": username}, UserRow)

    async def find_duplicate(self, username: str, email: str) -> UserRow | None:
        return await query_one(self.session, USER_SQL + " WHERE u.username=:username OR u.email=:email", {"username": username, "email": email}, UserRow)

    async def get_role(self, name: str) -> RoleRow:
        role = await query_one(self.session, "SELECT id, name FROM roles WHERE name=:name", {"name": name}, RoleRow)
        if role is None:
            raise LookupError(f"Missing role {name}")
        return role

    async def create(self, role_id: int, username: str, email: str, password_hash: str) -> UserRow:
        user_id = await scalar(
            self.session,
            "INSERT INTO users(role_id, username, email, password_hash, status) "
            "VALUES (:role_id, :username, :email, :password_hash, 'ACTIVE') RETURNING id",
            {"role_id": role_id, "username": username, "email": email, "password_hash": password_hash},
        )
        return await self.get(user_id)

    async def set_last_login(self, user_id: int, at: datetime) -> None:
        await execute(self.session, "UPDATE users SET last_login_at=:at, updated_at=now() WHERE id=:id", {"id": user_id, "at": at})

    async def list_users(self, offset: int, limit: int) -> list[UserRow]:
        return await query(self.session, USER_SQL + " ORDER BY u.id OFFSET :offset LIMIT :limit", {"offset": offset, "limit": limit}, UserRow)
