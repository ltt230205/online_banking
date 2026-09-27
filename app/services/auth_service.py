from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, conflict
from app.core.security import create_access_token, hash_password, verify_password
from app.repositories.customer_repository import CustomerRepository
from app.repositories.rows import CustomerRow, UserRow
from app.repositories.user_repository import UserRepository
from app.schemas.auth import EmployeeCreateRequest, LoginRequest, RegisterRequest
from app.services.audit_service import add_audit


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.customers = CustomerRepository(session)

    async def register(self, data: RegisterRequest) -> tuple[UserRow, CustomerRow]:
        if await self.users.find_duplicate(data.username, data.email):
            raise conflict("USER_ALREADY_EXISTS", "Username or email already exists")
        if await self.customers.identity_exists(data.identity_number):
            raise conflict("IDENTITY_ALREADY_EXISTS", "Identity number already exists")
        try:
            role = await self.users.get_role("CUSTOMER")
            user = await self.users.create(role.id, data.username, str(data.email), hash_password(data.password))
            customer = await self.customers.create(
                user.id, await self.customers.next_code(), data.full_name, data.date_of_birth,
                data.identity_number, data.phone, data.address,
            )
            await add_audit(self.session, user_id=user.id, action="CUSTOMER_CREATED", resource_type="customers", resource_id=customer.id)
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise conflict("DUPLICATE_DATA", "Email, username, phone or identity number already exists") from exc
        return user, customer

    async def login(self, data: LoginRequest) -> str:
        user = await self.users.get_by_username(data.username)
        if user is None or user.status != "ACTIVE" or not verify_password(data.password, user.password_hash):
            await add_audit(
                self.session, user_id=user.id if user else None, action="LOGIN_FAILED", resource_type="users",
                resource_id=user.id if user else None,
            )
            await self.session.commit()
            raise AppError("INVALID_CREDENTIALS", "Invalid username or password", 401)
        await self.users.set_last_login(user.id, datetime.now(UTC))
        await add_audit(self.session, user_id=user.id, action="LOGIN_SUCCESS", resource_type="users", resource_id=user.id)
        await self.session.commit()
        return create_access_token(user_id=user.id, username=user.username, role=user.role_name)

    async def create_employee(self, data: EmployeeCreateRequest, actor_id: int) -> UserRow:
        if await self.users.find_duplicate(data.username, data.email):
            raise conflict("USER_ALREADY_EXISTS", "Username or email already exists")
        try:
            role = await self.users.get_role("EMPLOYEE")
            user = await self.users.create(role.id, data.username, str(data.email), hash_password(data.password))
            await add_audit(self.session, user_id=actor_id, action="EMPLOYEE_CREATED", resource_type="users", resource_id=user.id)
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise conflict("USER_ALREADY_EXISTS", "Username or email already exists") from exc
        return user
