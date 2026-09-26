from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppError, conflict
from app.core.security import create_access_token, hash_password, verify_password
from app.models.entities import Customer, KycRequest, User
from app.repositories.customer_repository import CustomerRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import EmployeeCreateRequest, LoginRequest, RegisterRequest
from app.services.audit_service import add_audit


class AuthService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.customers = CustomerRepository(session)

    def register(self, data: RegisterRequest) -> tuple[User, Customer]:
        if self.users.find_duplicate(data.username, data.email):
            raise conflict("USER_ALREADY_EXISTS", "Username or email already exists")
        if self.customers.identity_exists(data.identity_number):
            raise conflict("IDENTITY_ALREADY_EXISTS", "Identity number already exists")
        role = self.users.get_role("CUSTOMER")
        user = User(
            role_id=role.id,
            username=data.username,
            email=str(data.email),
            password_hash=hash_password(data.password),
            status="ACTIVE",
        )
        self.session.add(user)
        self.session.flush()
        customer = Customer(
            user_id=user.id,
            customer_code=self.customers.next_code(),
            full_name=data.full_name,
            date_of_birth=data.date_of_birth,
            identity_number=data.identity_number,
            phone=data.phone,
            address=data.address,
            kyc_status="PENDING",
        )
        self.session.add(customer)
        self.session.flush()
        self.session.add(KycRequest(customer_id=customer.id, status="PENDING", document_data={}))
        add_audit(
            self.session,
            user_id=user.id,
            action="CUSTOMER_CREATED",
            resource_type="customers",
            resource_id=customer.id,
        )
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise conflict("DUPLICATE_DATA", "Email, username, phone or identity number already exists") from exc
        self.session.refresh(user)
        self.session.refresh(customer)
        return user, customer

    def login(self, data: LoginRequest) -> str:
        user = self.users.get_by_username(data.username)
        if user is None or user.status != "ACTIVE" or not verify_password(data.password, user.password_hash):
            add_audit(
                self.session,
                user_id=user.id if user else None,
                action="LOGIN_FAILED",
                resource_type="users",
                resource_id=user.id if user else None,
            )
            self.session.commit()
            raise AppError("INVALID_CREDENTIALS", "Invalid username or password", 401)
        user.last_login_at = datetime.now(UTC)
        add_audit(self.session, user_id=user.id, action="LOGIN_SUCCESS", resource_type="users", resource_id=user.id)
        self.session.commit()
        return create_access_token(user_id=user.id, username=user.username, role=user.role.name)

    def create_employee(self, data: EmployeeCreateRequest, actor_id: int) -> User:
        if self.users.find_duplicate(data.username, data.email):
            raise conflict("USER_ALREADY_EXISTS", "Username or email already exists")
        role = self.users.get_role("EMPLOYEE")
        user = User(
            role_id=role.id,
            username=data.username,
            email=str(data.email),
            password_hash=hash_password(data.password),
            status="ACTIVE",
        )
        self.session.add(user)
        self.session.flush()
        add_audit(self.session, user_id=actor_id, action="EMPLOYEE_CREATED", resource_type="users", resource_id=user.id)
        self.session.commit()
        self.session.refresh(user)
        return user
