from fastapi import Depends, FastAPI
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routers import accounts, admin, auth, customers, invoices, payees, payments, reports, transactions, transfers
from app.config import settings
from app.core.exceptions import AppError, register_exception_handlers
from app.api.dependencies import get_db
from app.services.system_service import SystemService


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Service-oriented backend for the Banking Management System.",
    openapi_tags=[
        {"name": "Authentication"},
        {"name": "Customers"},
        {"name": "Accounts"},
        {"name": "Transfers"},
        {"name": "Transactions"},
        {"name": "Payees"},
        {"name": "Invoices"},
        {"name": "Payments"},
        {"name": "Reports"},
        {"name": "Admin"},
        {"name": "System"},
    ],
)
register_exception_handlers(app)

api_prefix = "/api/v1"
for router in (
    auth.router,
    customers.router,
    accounts.router,
    transfers.router,
    transactions.router,
    payees.router,
    invoices.router,
    payments.router,
    reports.router,
    admin.router,
):
    app.include_router(router, prefix=api_prefix)


@app.get("/", tags=["System"])
def root() -> dict[str, str]:
    return {"message": settings.app_name, "docs": "/docs", "openapi": "/openapi.json"}


@app.get("/health", tags=["System"])
async def health(session: AsyncSession = Depends(get_db)) -> dict[str, str]:
    try:
        if not await SystemService(session).database_is_available():
            raise AppError("DATABASE_UNAVAILABLE", "Database is unavailable", 503)
    except SQLAlchemyError as exc:
        raise AppError("DATABASE_UNAVAILABLE", "Database is unavailable", 503) from exc
    return {"status": "ok", "database": "connected"}
