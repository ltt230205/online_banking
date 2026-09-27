from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, require_roles
from app.repositories.rows import UserRow
from app.schemas.invoice import InvoiceResponse
from app.services.invoice_service import InvoiceService


router = APIRouter(prefix="/invoices", tags=["Invoices"])


@router.get("", response_model=list[InvoiceResponse])
async def list_invoices(
    user: UserRow = Depends(require_roles("CUSTOMER")), session: AsyncSession = Depends(get_db)
) -> list[InvoiceResponse]:
    return await InvoiceService(session).list(user)


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: int,
    user: UserRow = Depends(require_roles("CUSTOMER")),
    session: AsyncSession = Depends(get_db),
) -> InvoiceResponse:
    return await InvoiceService(session).get(user, invoice_id)
