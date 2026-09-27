from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, require_roles
from app.repositories.rows import UserRow
from app.schemas.transaction import OtpVerifyRequest, PendingActionResponse, TransactionResponse, TransferRequest
from app.services.transfer_service import TransferService


router = APIRouter(prefix="/transfers", tags=["Transfers"])


@router.post("", response_model=PendingActionResponse, status_code=201)
async def create_transfer(
    data: TransferRequest,
    user: UserRow = Depends(require_roles("CUSTOMER")),
    session: AsyncSession = Depends(get_db),
) -> PendingActionResponse:
    service = TransferService(session)
    transaction, code = await service.create(user, data)
    return PendingActionResponse(
        transaction_id=transaction.id,
        status=transaction.status,
        message="OTP has been sent",
        development_otp=service.expose_otp(code),
    )


@router.post("/{transaction_id}/verify-otp", response_model=TransactionResponse)
async def verify_transfer(
    transaction_id: int,
    data: OtpVerifyRequest,
    user: UserRow = Depends(require_roles("CUSTOMER")),
    session: AsyncSession = Depends(get_db),
) -> TransactionResponse:
    return await TransferService(session).verify_and_execute(user, transaction_id, data.otp)
