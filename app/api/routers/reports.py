from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, require_roles
from app.models.entities import User
from app.schemas.report import CategoryExpense, MonthlyExpense, SummaryResponse
from app.services.report_service import ReportService


router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/me/summary", response_model=SummaryResponse)
def summary(
    user: User = Depends(require_roles("CUSTOMER")), session: Session = Depends(get_db)
) -> SummaryResponse:
    return ReportService(session).summary(user.id)


@router.get("/me/expenses-by-category", response_model=list[CategoryExpense])
def expenses_by_category(
    user: User = Depends(require_roles("CUSTOMER")), session: Session = Depends(get_db)
) -> list[CategoryExpense]:
    return ReportService(session).expenses_by_category(user.id)


@router.get("/me/monthly-expenses", response_model=list[MonthlyExpense])
def monthly_expenses(
    user: User = Depends(require_roles("CUSTOMER")), session: Session = Depends(get_db)
) -> list[MonthlyExpense]:
    return ReportService(session).monthly_expenses(user.id)
