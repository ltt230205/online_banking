from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, require_roles
from app.models.entities import User
from app.schemas.payee import PayeeCreateRequest, PayeeResponse
from app.services.payee_service import PayeeService


router = APIRouter(prefix="/payees", tags=["Payees"])


@router.get("", response_model=list[PayeeResponse])
def list_payees(
    user: User = Depends(require_roles("CUSTOMER")), session: Session = Depends(get_db)
) -> list[PayeeResponse]:
    return PayeeService(session).list(user)


@router.post("", response_model=PayeeResponse, status_code=201)
def create_payee(
    data: PayeeCreateRequest,
    user: User = Depends(require_roles("CUSTOMER")),
    session: Session = Depends(get_db),
) -> PayeeResponse:
    return PayeeService(session).create(user, data)


@router.delete("/{payee_id}", status_code=204)
def delete_payee(
    payee_id: int,
    user: User = Depends(require_roles("CUSTOMER")),
    session: Session = Depends(get_db),
) -> Response:
    PayeeService(session).delete(user, payee_id)
    return Response(status_code=204)
