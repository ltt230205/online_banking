from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, require_roles
from app.models.entities import Account, AuditLog, User
from app.repositories.customer_repository import CustomerRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import EmployeeCreateRequest, UserResponse
from app.schemas.account import AccountResponse
from app.schemas.customer import CustomerResponse, KycUpdateRequest
from app.schemas.report import AdminTransactionReport
from app.services.auth_service import AuthService
from app.services.customer_service import CustomerService
from app.services.report_service import ReportService


router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/customers", response_model=list[CustomerResponse])
def list_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    kyc_status: str | None = None,
    _: User = Depends(require_roles("ADMIN", "EMPLOYEE")),
    session: Session = Depends(get_db),
) -> list[CustomerResponse]:
    return CustomerRepository(session).list((page - 1) * page_size, page_size, kyc_status)


@router.put("/customers/{customer_id}/kyc", response_model=CustomerResponse)
def review_kyc(
    customer_id: int,
    data: KycUpdateRequest,
    user: User = Depends(require_roles("ADMIN", "EMPLOYEE")),
    session: Session = Depends(get_db),
) -> CustomerResponse:
    return CustomerService(session).review_kyc(customer_id, data.status, data.rejection_reason, user.id)


@router.get("/users", response_model=list[UserResponse])
def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _: User = Depends(require_roles("ADMIN")),
    session: Session = Depends(get_db),
) -> list[UserResponse]:
    return UserRepository(session).list_users((page - 1) * page_size, page_size)


@router.get("/accounts", response_model=list[AccountResponse])
def list_all_accounts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _: User = Depends(require_roles("ADMIN", "EMPLOYEE")),
    session: Session = Depends(get_db),
) -> list[AccountResponse]:
    return list(
        session.scalars(
            select(Account)
            .where(Account.is_deleted.is_(False))
            .order_by(Account.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )


@router.post("/employees", response_model=UserResponse, status_code=201)
def create_employee(
    data: EmployeeCreateRequest,
    user: User = Depends(require_roles("ADMIN")),
    session: Session = Depends(get_db),
) -> UserResponse:
    return AuthService(session).create_employee(data, user.id)


@router.get("/reports/transactions", response_model=AdminTransactionReport)
def transaction_report(
    _: User = Depends(require_roles("ADMIN")), session: Session = Depends(get_db)
) -> AdminTransactionReport:
    return ReportService(session).admin_transactions()


@router.get("/audit-logs")
def audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _: User = Depends(require_roles("ADMIN")),
    session: Session = Depends(get_db),
) -> list[dict[str, object]]:
    rows = session.scalars(
        select(AuditLog).order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    return [
        {
            "id": row.id,
            "user_id": row.user_id,
            "action": row.action,
            "resource_type": row.resource_type,
            "resource_id": row.resource_id,
            "created_at": row.created_at,
        }
        for row in rows
    ]
