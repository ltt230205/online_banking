from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, require_roles
from app.models.entities import User
from app.schemas.transaction import OtpVerifyRequest, PendingActionResponse, TransactionResponse, TransferRequest
from app.services.transfer_service import TransferService


router = APIRouter(prefix="/transfers", tags=["Transfers"])


@router.post("", response_model=PendingActionResponse, status_code=201)
def create_transfer(
    data: TransferRequest,
    user: User = Depends(require_roles("CUSTOMER")),
    session: Session = Depends(get_db),
) -> PendingActionResponse:
    service = TransferService(session)
    transaction, code = service.create(user, data)
    return PendingActionResponse(
        transaction_id=transaction.id,
        status=transaction.status,
        message="OTP has been sent",
        development_otp=service.expose_otp(code),
    )


@router.post("/{transaction_id}/verify-otp", response_model=TransactionResponse)
def verify_transfer(
    transaction_id: int,
    data: OtpVerifyRequest,
    user: User = Depends(require_roles("CUSTOMER")),
    session: Session = Depends(get_db),
) -> TransactionResponse:
    return TransferService(session).verify_and_execute(user, transaction_id, data.otp)
