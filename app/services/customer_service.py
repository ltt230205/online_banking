from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, not_found
from app.repositories.customer_repository import CustomerRepository
from app.repositories.rows import CustomerRow
from app.services.audit_service import add_audit
from app.services.notification_service import NotificationService


def mask_identity(value: str) -> str:
    return "*" * max(len(value) - 4, 0) + value[-4:]


class CustomerService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.customers = CustomerRepository(session)

    async def get_for_user(self, user_id: int) -> CustomerRow:
        customer = await self.customers.get_by_user_id(user_id)
        if customer is None:
            raise not_found("CUSTOMER_NOT_FOUND", "Customer profile not found")
        return customer

    async def review_kyc(self, customer_id: int, status: str, reason: str | None, actor_id: int) -> CustomerRow:
        customer = await self.customers.get(customer_id)
        if customer is None:
            raise not_found("CUSTOMER_NOT_FOUND", "Customer not found")
        if status == "REJECTED" and not reason:
            raise AppError("REJECTION_REASON_REQUIRED", "Rejection reason is required", 422)
        before = {"kyc_status": customer.kyc_status, "version": customer.version}
        updated = await self.customers.update_kyc(customer, status, datetime.now(UTC) if status == "VERIFIED" else None)
        if updated is None:
            raise AppError("VERSION_CONFLICT", "Customer was modified concurrently", 409)
        await self.customers.close_pending_kyc(customer.id, "APPROVED" if status == "VERIFIED" else "REJECTED", actor_id, reason)
        await add_audit(
            self.session, user_id=actor_id, action="KYC_APPROVED" if status == "VERIFIED" else "KYC_REJECTED",
            resource_type="customers", resource_id=customer.id, before=before,
            after={"kyc_status": updated.kyc_status, "version": updated.version},
        )
        await NotificationService(self.session).create_in_app(
            customer.user_id, "KYC_APPROVED" if status == "VERIFIED" else "KYC_REJECTED",
            "Kết quả KYC", "Hồ sơ KYC đã được duyệt." if status == "VERIFIED" else "Hồ sơ KYC bị từ chối.",
        )
        await self.session.commit()
        return updated
