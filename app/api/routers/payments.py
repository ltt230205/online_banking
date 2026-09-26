from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, require_roles
from app.models.entities import User
from app.schemas.payment import PaymentRequest, PaymentResult
from app.schemas.transaction import OtpVerifyRequest, PendingActionResponse
from app.services.payment_service import PaymentService


router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("", response_model=PendingActionResponse, status_code=201)
def create_payment(
    data: PaymentRequest,
    user: User = Depends(require_roles("CUSTOMER")),
    session: Session = Depends(get_db),
) -> PendingActionResponse:
    service = PaymentService(session)
    payment, code = service.create(user, data.invoice_id, data.account_id)
    return PendingActionResponse(
        payment_id=payment.id,
        status=payment.status,
        message="OTP has been sent",
        development_otp=service.expose_otp(code),
    )


@router.post("/{payment_id}/verify-otp", response_model=PaymentResult)
def verify_payment(
    payment_id: int,
    data: OtpVerifyRequest,
    user: User = Depends(require_roles("CUSTOMER")),
    session: Session = Depends(get_db),
) -> PaymentResult:
    payment = PaymentService(session).verify_and_execute(user, payment_id, data.otp)
    return PaymentResult(
        payment_id=payment.id,
        transaction_id=payment.transaction_id,
        status=payment.status,
        amount=payment.amount,
    )
