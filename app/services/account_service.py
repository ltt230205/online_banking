from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import forbidden, not_found
from app.models.entities import Transaction, TransactionEntry
from app.repositories.account_repository import AccountRepository
from app.repositories.customer_repository import CustomerRepository
from app.schemas.account import StatementEntry, StatementResponse


class AccountService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.accounts = AccountRepository(session)
        self.customers = CustomerRepository(session)

    def customer_for_user(self, user_id: int):
        customer = self.customers.get_by_user_id(user_id)
        if customer is None:
            raise not_found("CUSTOMER_NOT_FOUND", "Customer profile not found")
        return customer

    def list_for_user(self, user_id: int):
        return self.accounts.list_for_customer(self.customer_for_user(user_id).id)

    def get_authorized(self, account_id: int, user: object):
        account = self.accounts.get(account_id)
        if account is None:
            raise not_found("ACCOUNT_NOT_FOUND", "Account not found")
        if user.role.name == "CUSTOMER":
            customer = self.customer_for_user(user.id)
            if account.customer_id != customer.id:
                raise forbidden()
        return account

    def statement(self, account_id: int, user: object, from_date: datetime, to_date: datetime) -> StatementResponse:
        if from_date >= to_date:
            raise ValueError("from_date must be before to_date")
        account = self.get_authorized(account_id, user)
        rows = list(
            self.session.execute(
                select(TransactionEntry, Transaction)
                .join(Transaction, Transaction.id == TransactionEntry.transaction_id)
                .where(
                    TransactionEntry.account_id == account.id,
                    TransactionEntry.created_at >= from_date,
                    TransactionEntry.created_at <= to_date,
                    Transaction.status == "SUCCESS",
                )
                .order_by(TransactionEntry.created_at, TransactionEntry.id)
            )
        )
        if rows:
            opening = rows[0][0].balance_before
            closing = rows[-1][0].balance_after
        else:
            previous = self.session.scalar(
                select(TransactionEntry)
                .join(Transaction, Transaction.id == TransactionEntry.transaction_id)
                .where(
                    TransactionEntry.account_id == account.id,
                    TransactionEntry.created_at < from_date,
                    Transaction.status == "SUCCESS",
                )
                .order_by(TransactionEntry.created_at.desc(), TransactionEntry.id.desc())
            )
            opening = previous.balance_after if previous else account.balance
            closing = opening
        entries = [
            StatementEntry(
                date=entry.created_at,
                transaction_code=transaction.transaction_code,
                description=transaction.description,
                debit=entry.amount if entry.entry_type == "DEBIT" else Decimal("0"),
                credit=entry.amount if entry.entry_type == "CREDIT" else Decimal("0"),
                balance=entry.balance_after,
            )
            for entry, transaction in rows
        ]
        return StatementResponse(
            account_number=account.account_number,
            customer_name=account.customer.full_name,
            from_date=from_date.astimezone(UTC),
            to_date=to_date.astimezone(UTC),
            opening_balance=opening,
            closing_balance=closing,
            transactions=entries,
        )
