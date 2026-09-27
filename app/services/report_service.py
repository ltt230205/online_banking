from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.core.exceptions import not_found
from app.models.entities import Account, Transaction, TransactionEntry
from app.repositories.customer_repository import CustomerRepository
from app.schemas.report import AdminTransactionReport, CategoryExpense, MonthlyExpense, SummaryResponse


class ReportService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.customers = CustomerRepository(session)

    def _customer_id(self, user_id: int) -> int:
        customer = self.customers.get_by_user_id(user_id)
        if customer is None:
            raise not_found("CUSTOMER_NOT_FOUND", "Customer profile not found")
        return customer.id

    def summary(self, user_id: int) -> SummaryResponse:
        customer_id = self._customer_id(user_id)
        total_balance = self.session.scalar(
            select(func.coalesce(func.sum(Account.balance), 0)).where(
                Account.customer_id == customer_id, Account.is_deleted.is_(False)
            )
        )
        income, expense, count = self.session.execute(
            select(
                func.coalesce(func.sum(case((TransactionEntry.entry_type == "CREDIT", TransactionEntry.amount), else_=0)), 0),
                func.coalesce(func.sum(case((TransactionEntry.entry_type == "DEBIT", TransactionEntry.amount), else_=0)), 0),
                func.count(TransactionEntry.id),
            )
            .join(Account, Account.id == TransactionEntry.account_id)
            .join(Transaction, Transaction.id == TransactionEntry.transaction_id)
            .where(Account.customer_id == customer_id, Transaction.status == "SUCCESS")
        ).one()
        return SummaryResponse(
            total_balance=Decimal(total_balance),
            total_income=Decimal(income),
            total_expense=Decimal(expense),
            transaction_count=int(count),
        )

    def expenses_by_category(self, user_id: int) -> list[CategoryExpense]:
        customer_id = self._customer_id(user_id)
        rows = self.session.execute(
            select(Transaction.transaction_type, func.sum(TransactionEntry.amount))
            .join(TransactionEntry, TransactionEntry.transaction_id == Transaction.id)
            .join(Account, Account.id == TransactionEntry.account_id)
            .where(
                Account.customer_id == customer_id,
                TransactionEntry.entry_type == "DEBIT",
                Transaction.status == "SUCCESS",
            )
            .group_by(Transaction.transaction_type)
            .order_by(Transaction.transaction_type)
        )
        return [CategoryExpense(category=category, amount=amount) for category, amount in rows]

    def monthly_expenses(self, user_id: int) -> list[MonthlyExpense]:
        customer_id = self._customer_id(user_id)
        month = func.to_char(TransactionEntry.created_at, "YYYY-MM")
        rows = self.session.execute(
            select(month.label("month"), func.sum(TransactionEntry.amount))
            .join(Transaction, Transaction.id == TransactionEntry.transaction_id)
            .join(Account, Account.id == TransactionEntry.account_id)
            .where(
                Account.customer_id == customer_id,
                TransactionEntry.entry_type == "DEBIT",
                Transaction.status == "SUCCESS",
            )
            .group_by(month)
            .order_by(month)
        )
        return [MonthlyExpense(month=value, amount=amount) for value, amount in rows]

    def admin_transactions(self) -> AdminTransactionReport:
        total, successful, failed, amount = self.session.execute(
            select(
                func.count(Transaction.id),
                func.count(Transaction.id).filter(Transaction.status == "SUCCESS"),
                func.count(Transaction.id).filter(Transaction.status == "FAILED"),
                func.coalesce(
                    func.sum(Transaction.amount).filter(
                        Transaction.status == "SUCCESS",
                        Transaction.transaction_type.in_(["INTERNAL_TRANSFER", "INTERBANK_TRANSFER"]),
                    ),
                    0,
                ),
            )
        ).one()
        return AdminTransactionReport(
            total_transactions=int(total),
            successful_transactions=int(successful),
            failed_transactions=int(failed),
            total_transfer_amount=Decimal(amount),
        )
