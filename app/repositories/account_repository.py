from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Account


class AccountRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_for_customer(self, customer_id: int) -> list[Account]:
        return list(
            self.session.scalars(
                select(Account).where(Account.customer_id == customer_id, Account.is_deleted.is_(False)).order_by(Account.id)
            )
        )

    def get(self, account_id: int) -> Account | None:
        return self.session.scalar(
            select(Account).where(Account.id == account_id, Account.is_deleted.is_(False))
        )

    def get_by_number(self, account_number: str) -> Account | None:
        return self.session.scalar(
            select(Account).where(Account.account_number == account_number, Account.is_deleted.is_(False))
        )

    def lock_accounts(self, account_ids: list[int]) -> dict[int, Account]:
        rows = self.session.scalars(
            select(Account).where(Account.id.in_(sorted(set(account_ids)))).order_by(Account.id).with_for_update()
        )
        return {account.id: account for account in rows}
