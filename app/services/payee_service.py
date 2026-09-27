from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import conflict, forbidden, not_found
from app.repositories.account_repository import AccountRepository
from app.repositories.customer_repository import CustomerRepository
from app.repositories.payee_repository import PayeeRepository
from app.repositories.rows import PayeeRow, UserRow
from app.schemas.payee import PayeeCreateRequest
from app.services.audit_service import add_audit


class PayeeService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.customers = CustomerRepository(session)
        self.accounts = AccountRepository(session)
        self.payees = PayeeRepository(session)

    async def _customer(self, user_id: int):
        customer = await self.customers.get_by_user_id(user_id)
        if customer is None:
            raise not_found("CUSTOMER_NOT_FOUND", "Customer profile not found")
        return customer

    async def list(self, user: UserRow) -> list[PayeeRow]:
        return await self.payees.list((await self._customer(user.id)).id)

    async def create(self, user: UserRow, data: PayeeCreateRequest) -> PayeeRow:
        customer = await self._customer(user.id)
        linked = await self.accounts.get_by_number(data.account_number)
        try:
            payee = await self.payees.create(
                customer.id, data.nickname or data.name, data.account_number, data.name,
                data.bank_name.upper(), linked.id if linked else None,
            )
            await add_audit(self.session, user_id=user.id, action="PAYEE_CREATED", resource_type="payees", resource_id=payee.id)
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise conflict("PAYEE_ALREADY_EXISTS", "Payee already exists") from exc
        return payee

    async def delete(self, user: UserRow, payee_id: int) -> None:
        customer = await self._customer(user.id)
        payee = await self.payees.get(payee_id)
        if payee is None:
            raise not_found("PAYEE_NOT_FOUND", "Payee not found")
        if payee.customer_id != customer.id:
            raise forbidden()
        await self.payees.soft_delete(payee_id, user.id, datetime.now(UTC))
        await add_audit(self.session, user_id=user.id, action="PAYEE_DELETED", resource_type="payees", resource_id=payee.id)
        await self.session.commit()
