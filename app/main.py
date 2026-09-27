import psycopg
from fastapi import FastAPI

from app.api.routers import accounts, admin, auth, customers, invoices, payees, payments, reports, transactions, transfers
from app.config import settings
from app.core.exceptions import AppError, register_exception_handlers


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
def health() -> dict[str, str]:
    try:
        with psycopg.connect(
            dbname=settings.postgres_db,
            user=settings.postgres_user,
            password=settings.postgres_password.get_secret_value(),
            host=settings.postgres_host,
            port=settings.postgres_port,
            connect_timeout=3,
        ) as connection:
            connection.execute("SELECT 1").fetchone()
    except psycopg.Error as exc:
        raise AppError("DATABASE_UNAVAILABLE", "Database is unavailable", 503) from exc
    return {"status": "ok", "database": "connected"}
