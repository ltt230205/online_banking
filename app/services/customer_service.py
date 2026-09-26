from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError, not_found
from app.models.entities import KycRequest, User
from app.repositories.customer_repository import CustomerRepository
from app.services.audit_service import add_audit
from app.services.notification_service import NotificationService


def mask_identity(value: str) -> str:
    return "*" * max(len(value) - 4, 0) + value[-4:]


class CustomerService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.customers = CustomerRepository(session)

    def get_for_user(self, user_id: int):
        customer = self.customers.get_by_user_id(user_id)
        if customer is None:
            raise not_found("CUSTOMER_NOT_FOUND", "Customer profile not found")
        return customer

    def review_kyc(self, customer_id: int, status: str, reason: str | None, actor_id: int):
        customer = self.customers.get(customer_id)
        if customer is None:
            raise not_found("CUSTOMER_NOT_FOUND", "Customer not found")
        if status == "REJECTED" and not reason:
            raise AppError("REJECTION_REASON_REQUIRED", "Rejection reason is required", 422)
        before = {"kyc_status": customer.kyc_status, "version": customer.version}
        customer.kyc_status = status
        customer.kyc_verified_at = datetime.now(UTC) if status == "VERIFIED" else None
        customer.version += 1
        request = self.session.scalar(
            select(KycRequest)
            .where(KycRequest.customer_id == customer.id, KycRequest.status == "PENDING")
            .order_by(KycRequest.submitted_at.desc())
            .with_for_update()
        )
        if request:
            request.status = "APPROVED" if status == "VERIFIED" else "REJECTED"
            request.reviewed_by = actor_id
            request.reviewed_at = datetime.now(UTC)
            request.rejection_reason = reason
        add_audit(
            self.session,
            user_id=actor_id,
            action="KYC_APPROVED" if status == "VERIFIED" else "KYC_REJECTED",
            resource_type="customers",
            resource_id=customer.id,
            before=before,
            after={"kyc_status": customer.kyc_status, "version": customer.version},
        )
        NotificationService(self.session).create_in_app(
            customer.user_id,
            "KYC_APPROVED" if status == "VERIFIED" else "KYC_REJECTED",
            "Kết quả KYC",
            "Hồ sơ KYC đã được duyệt." if status == "VERIFIED" else "Hồ sơ KYC bị từ chối.",
        )
        self.session.commit()
        self.session.refresh(customer)
        return customer
