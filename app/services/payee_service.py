from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import conflict, forbidden, not_found
from app.models.entities import Payee, User
from app.repositories.account_repository import AccountRepository
from app.repositories.customer_repository import CustomerRepository
from app.repositories.payee_repository import PayeeRepository
from app.schemas.payee import PayeeCreateRequest
from app.services.audit_service import add_audit


class PayeeService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.customers = CustomerRepository(session)
        self.accounts = AccountRepository(session)
        self.payees = PayeeRepository(session)

    def _customer(self, user_id: int):
        customer = self.customers.get_by_user_id(user_id)
        if customer is None:
            raise not_found("CUSTOMER_NOT_FOUND", "Customer profile not found")
        return customer

    def list(self, user: User):
        return self.payees.list(self._customer(user.id).id)

    def create(self, user: User, data: PayeeCreateRequest) -> Payee:
        customer = self._customer(user.id)
        linked = self.accounts.get_by_number(data.account_number)
        payee = Payee(
            customer_id=customer.id,
            nickname=data.nickname or data.name,
            account_number=data.account_number,
            account_name=data.name,
            bank_code=data.bank_name.upper(),
            is_internal=linked is not None,
            linked_account_id=linked.id if linked else None,
        )
        self.session.add(payee)
        try:
            self.session.flush()
        except IntegrityError as exc:
            self.session.rollback()
            raise conflict("PAYEE_ALREADY_EXISTS", "Payee already exists") from exc
        add_audit(self.session, user_id=user.id, action="PAYEE_CREATED", resource_type="payees", resource_id=payee.id)
        self.session.commit()
        self.session.refresh(payee)
        return payee

    def delete(self, user: User, payee_id: int) -> None:
        customer = self._customer(user.id)
        payee = self.payees.get(payee_id)
        if payee is None:
            raise not_found("PAYEE_NOT_FOUND", "Payee not found")
        if payee.customer_id != customer.id:
            raise forbidden()
        payee.is_deleted = True
        payee.deleted_at = datetime.now(UTC)
        payee.deleted_by = user.id
        add_audit(self.session, user_id=user.id, action="PAYEE_DELETED", resource_type="payees", resource_id=payee.id)
        self.session.commit()
