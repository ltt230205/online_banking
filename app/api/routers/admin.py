from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, require_roles
from app.repositories.rows import UserRow
from app.repositories.account_repository import AccountRepository
from app.repositories.audit_repository import AuditRepository
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
async def list_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    kyc_status: str | None = None,
    _: UserRow = Depends(require_roles("ADMIN", "EMPLOYEE")),
    session: AsyncSession = Depends(get_db),
) -> list[CustomerResponse]:
    return await CustomerRepository(session).list((page - 1) * page_size, page_size, kyc_status)


@router.put("/customers/{customer_id}/kyc", response_model=CustomerResponse)
async def review_kyc(
    customer_id: int,
    data: KycUpdateRequest,
    user: UserRow = Depends(require_roles("ADMIN", "EMPLOYEE")),
    session: AsyncSession = Depends(get_db),
) -> CustomerResponse:
    return await CustomerService(session).review_kyc(customer_id, data.status, data.rejection_reason, user.id)


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _: UserRow = Depends(require_roles("ADMIN")),
    session: AsyncSession = Depends(get_db),
) -> list[UserResponse]:
    return await UserRepository(session).list_users((page - 1) * page_size, page_size)


@router.get("/accounts", response_model=list[AccountResponse])
async def list_all_accounts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _: UserRow = Depends(require_roles("ADMIN", "EMPLOYEE")),
    session: AsyncSession = Depends(get_db),
) -> list[AccountResponse]:
    return await AccountRepository(session).list_all((page - 1) * page_size, page_size)


@router.post("/employees", response_model=UserResponse, status_code=201)
async def create_employee(
    data: EmployeeCreateRequest,
    user: UserRow = Depends(require_roles("ADMIN")),
    session: AsyncSession = Depends(get_db),
) -> UserResponse:
    return await AuthService(session).create_employee(data, user.id)


@router.get("/reports/transactions", response_model=AdminTransactionReport)
async def transaction_report(
    _: UserRow = Depends(require_roles("ADMIN")), session: AsyncSession = Depends(get_db)
) -> AdminTransactionReport:
    return await ReportService(session).admin_transactions()


@router.get("/audit-logs")
async def audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _: UserRow = Depends(require_roles("ADMIN")),
    session: AsyncSession = Depends(get_db),
) -> list[dict[str, object]]:
    rows = await AuditRepository(session).list((page - 1) * page_size, page_size)
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
