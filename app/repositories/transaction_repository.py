from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.entities import Account, Transaction


class TransactionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, transaction_id: int, *, lock: bool = False) -> Transaction | None:
        query = select(Transaction).where(Transaction.id == transaction_id)
        if lock:
            query = query.with_for_update()
        return self.session.scalar(query)

    def list(
        self,
        *,
        customer_id: int | None,
        page: int,
        page_size: int,
        transaction_type: str | None,
        status: str | None,
        from_date: datetime | None,
        to_date: datetime | None,
    ) -> tuple[list[Transaction], int]:
        query = select(Transaction)
        if customer_id is not None:
            account_ids = select(Account.id).where(Account.customer_id == customer_id)
            query = query.where(
                or_(Transaction.source_account_id.in_(account_ids), Transaction.destination_account_id.in_(account_ids))
            )
        if transaction_type:
            query = query.where(Transaction.transaction_type == transaction_type)
        if status:
            query = query.where(Transaction.status == status)
        if from_date:
            query = query.where(Transaction.created_at >= from_date)
        if to_date:
            query = query.where(Transaction.created_at <= to_date)
        total = int(self.session.scalar(select(func.count()).select_from(query.subquery())) or 0)
        items = list(
            self.session.scalars(
                query.order_by(Transaction.created_at.desc(), Transaction.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        return items, total
