from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, require_roles
from app.models.entities import User
from app.schemas.invoice import InvoiceResponse
from app.services.invoice_service import InvoiceService


router = APIRouter(prefix="/invoices", tags=["Invoices"])


@router.get("", response_model=list[InvoiceResponse])
def list_invoices(
    user: User = Depends(require_roles("CUSTOMER")), session: Session = Depends(get_db)
) -> list[InvoiceResponse]:
    return InvoiceService(session).list(user)


@router.get("/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(
    invoice_id: int,
    user: User = Depends(require_roles("CUSTOMER")),
    session: Session = Depends(get_db),
) -> InvoiceResponse:
    return InvoiceService(session).get(user, invoice_id)
