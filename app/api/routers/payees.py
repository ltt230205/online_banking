from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, require_roles
from app.repositories.rows import UserRow
from app.schemas.payee import PayeeCreateRequest, PayeeResponse
from app.services.payee_service import PayeeService


router = APIRouter(prefix="/payees", tags=["Payees"])


@router.get("", response_model=list[PayeeResponse])
async def list_payees(
    user: UserRow = Depends(require_roles("CUSTOMER")), session: AsyncSession = Depends(get_db)
) -> list[PayeeResponse]:
    return await PayeeService(session).list(user)


@router.post("", response_model=PayeeResponse, status_code=201)
async def create_payee(
    data: PayeeCreateRequest,
    user: UserRow = Depends(require_roles("CUSTOMER")),
    session: AsyncSession = Depends(get_db),
) -> PayeeResponse:
    return await PayeeService(session).create(user, data)


@router.delete("/{payee_id}", status_code=204)
async def delete_payee(
    payee_id: int,
    user: UserRow = Depends(require_roles("CUSTOMER")),
    session: AsyncSession = Depends(get_db),
) -> Response:
    await PayeeService(session).delete(user, payee_id)
    return Response(status_code=204)
