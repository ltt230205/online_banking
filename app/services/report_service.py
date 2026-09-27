from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import not_found
from app.repositories.customer_repository import CustomerRepository
from app.repositories.report_repository import ReportRepository


class ReportService:
    def __init__(self, session: AsyncSession) -> None:
        self.customers = CustomerRepository(session)
        self.reports = ReportRepository(session)

    async def _customer_id(self, user_id: int) -> int:
        customer = await self.customers.get_by_user_id(user_id)
        if customer is None:
            raise not_found("CUSTOMER_NOT_FOUND", "Customer profile not found")
        return customer.id

    async def summary(self, user_id: int):
        return await self.reports.summary(await self._customer_id(user_id))

    async def expenses_by_category(self, user_id: int):
        return await self.reports.expenses_by_category(await self._customer_id(user_id))

    async def monthly_expenses(self, user_id: int):
        return await self.reports.monthly_expenses(await self._customer_id(user_id))

    async def admin_transactions(self):
        return await self.reports.admin_transactions()
