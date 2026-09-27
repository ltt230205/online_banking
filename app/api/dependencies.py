from collections.abc import Callable, AsyncGenerator

import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, forbidden
from app.core.security import decode_access_token
from app.db.session import AsyncSessionLocal
from app.repositories.rows import UserRow
from app.repositories.user_repository import UserRepository


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def get_current_user(token: str = Depends(oauth2_scheme), session: AsyncSession = Depends(get_db)) -> UserRow:
    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
        raise AppError("INVALID_TOKEN", "Authentication token is invalid or expired", 401) from exc
    user = await UserRepository(session).get(user_id)
    if user is None or user.status != "ACTIVE":
        raise AppError("INVALID_TOKEN", "User is unavailable", 401)
    return user


def require_roles(*roles: str) -> Callable[..., UserRow]:
    async def dependency(user: UserRow = Depends(get_current_user)) -> UserRow:
        if user.role_name not in roles:
            raise forbidden()
        return user

    return dependency
