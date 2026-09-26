from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.entities import Role, User


class UserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_username(self, username: str) -> User | None:
        return self.session.scalar(select(User).where(User.username == username, User.is_deleted.is_(False)))

    def find_duplicate(self, username: str, email: str) -> User | None:
        return self.session.scalar(select(User).where(or_(User.username == username, User.email == email)))

    def get_role(self, name: str) -> Role:
        return self.session.scalars(select(Role).where(Role.name == name)).one()

    def list_users(self, offset: int, limit: int) -> list[User]:
        return list(self.session.scalars(select(User).order_by(User.id).offset(offset).limit(limit)))
