from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db
from app.repositories.rows import UserRow
from app.schemas.transaction import TransactionPage
from app.services.transaction_service import TransactionService


router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.get("", response_model=TransactionPage)
async def list_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    type: str | None = Query(None),
    status: str | None = Query(None),
    from_date: datetime | None = Query(None),
    to_date: datetime | None = Query(None),
    user: UserRow = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TransactionPage:
    items, total = await TransactionService(session).list(
        user=user,
        page=page,
        page_size=page_size,
        transaction_type=type,
        status=status,
        from_date=from_date,
        to_date=to_date,
    )
    return TransactionPage(items=items, page=page, page_size=page_size, total=total)
