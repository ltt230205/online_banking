from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db, require_roles
from app.core.exceptions import AppError
from app.repositories.rows import UserRow
from app.schemas.account import AccountResponse, BalanceResponse, StatementResponse
from app.services.account_service import AccountService


router = APIRouter(prefix="/accounts", tags=["Accounts"])


@router.get("", response_model=list[AccountResponse])
async def list_accounts(
    user: UserRow = Depends(require_roles("CUSTOMER")), session: AsyncSession = Depends(get_db)
) -> list[AccountResponse]:
    return await AccountService(session).list_for_user(user.id)


@router.get("/{account_id}", response_model=AccountResponse)
async def get_account(
    account_id: int, user: UserRow = Depends(get_current_user), session: AsyncSession = Depends(get_db)
) -> AccountResponse:
    return await AccountService(session).get_authorized(account_id, user)


@router.get("/{account_id}/balance", response_model=BalanceResponse)
async def get_balance(
    account_id: int, user: UserRow = Depends(get_current_user), session: AsyncSession = Depends(get_db)
) -> BalanceResponse:
    account = await AccountService(session).get_authorized(account_id, user)
    return BalanceResponse(account_number=account.account_number, balance=account.balance, currency=account.currency)


@router.get("/{account_id}/statement", response_model=StatementResponse)
async def statement(
    account_id: int,
    from_date: datetime = Query(default_factory=lambda: datetime.now(UTC) - timedelta(days=30)),
    to_date: datetime = Query(default_factory=lambda: datetime.now(UTC)),
    user: UserRow = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> StatementResponse:
    try:
        return await AccountService(session).statement(account_id, user, from_date, to_date)
    except ValueError as exc:
        raise AppError("INVALID_DATE_RANGE", str(exc), 422) from exc
