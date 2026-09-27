from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, require_roles
from app.repositories.rows import UserRow
from app.schemas.report import CategoryExpense, MonthlyExpense, SummaryResponse
from app.services.report_service import ReportService


router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/me/summary", response_model=SummaryResponse)
async def summary(
    user: UserRow = Depends(require_roles("CUSTOMER")), session: AsyncSession = Depends(get_db)
) -> SummaryResponse:
    return await ReportService(session).summary(user.id)


@router.get("/me/expenses-by-category", response_model=list[CategoryExpense])
async def expenses_by_category(
    user: UserRow = Depends(require_roles("CUSTOMER")), session: AsyncSession = Depends(get_db)
) -> list[CategoryExpense]:
    return await ReportService(session).expenses_by_category(user.id)


@router.get("/me/monthly-expenses", response_model=list[MonthlyExpense])
async def monthly_expenses(
    user: UserRow = Depends(require_roles("CUSTOMER")), session: AsyncSession = Depends(get_db)
) -> list[MonthlyExpense]:
    return await ReportService(session).monthly_expenses(user.id)
