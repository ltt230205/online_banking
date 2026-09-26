from collections.abc import Callable, Generator

import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError, forbidden
from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.models.entities import User


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


def get_db() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_db)) -> User:
    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
        raise AppError("INVALID_TOKEN", "Authentication token is invalid or expired", 401) from exc
    user = session.scalar(select(User).where(User.id == user_id, User.is_deleted.is_(False)))
    if user is None or user.status != "ACTIVE":
        raise AppError("INVALID_TOKEN", "User is unavailable", 401)
    return user


def require_roles(*roles: str) -> Callable[..., User]:
    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role.name not in roles:
            raise forbidden()
        return user

    return dependency
