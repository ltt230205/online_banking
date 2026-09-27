from sqlalchemy.ext.asyncio import AsyncSession

from app.common.db import query, query_one
from app.repositories.rows import AdminTransactionReportRow, CategoryExpenseRow, MonthlyExpenseRow, SummaryRow


class ReportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def summary(self, customer_id: int) -> SummaryRow:
        return await query_one(
            self.session,
            "SELECT (SELECT COALESCE(SUM(balance),0) FROM accounts WHERE customer_id=:id AND is_deleted=false) AS total_balance, "
            "COALESCE(SUM(CASE WHEN e.entry_type='CREDIT' THEN e.amount ELSE 0 END),0) AS total_income, "
            "COALESCE(SUM(CASE WHEN e.entry_type='DEBIT' THEN e.amount ELSE 0 END),0) AS total_expense, "
            "COUNT(e.id) AS transaction_count FROM transaction_entries e "
            "JOIN accounts a ON a.id=e.account_id JOIN transactions t ON t.id=e.transaction_id "
            "WHERE a.customer_id=:id AND t.status='SUCCESS'",
            {"id": customer_id}, SummaryRow,
        )

    async def expenses_by_category(self, customer_id: int) -> list[CategoryExpenseRow]:
        return await query(
            self.session,
            "SELECT t.transaction_type AS category, SUM(e.amount) AS amount FROM transactions t "
            "JOIN transaction_entries e ON e.transaction_id=t.id JOIN accounts a ON a.id=e.account_id "
            "WHERE a.customer_id=:id AND e.entry_type='DEBIT' AND t.status='SUCCESS' "
            "GROUP BY t.transaction_type ORDER BY t.transaction_type",
            {"id": customer_id}, CategoryExpenseRow,
        )

    async def monthly_expenses(self, customer_id: int) -> list[MonthlyExpenseRow]:
        return await query(
            self.session,
            "SELECT to_char(e.created_at,'YYYY-MM') AS month, SUM(e.amount) AS amount FROM transaction_entries e "
            "JOIN transactions t ON t.id=e.transaction_id JOIN accounts a ON a.id=e.account_id "
            "WHERE a.customer_id=:id AND e.entry_type='DEBIT' AND t.status='SUCCESS' "
            "GROUP BY to_char(e.created_at,'YYYY-MM') ORDER BY month",
            {"id": customer_id}, MonthlyExpenseRow,
        )

    async def admin_transactions(self) -> AdminTransactionReportRow:
        return await query_one(
            self.session,
            "SELECT COUNT(*) AS total_transactions, COUNT(*) FILTER (WHERE status='SUCCESS') AS successful_transactions, "
            "COUNT(*) FILTER (WHERE status='FAILED') AS failed_transactions, "
            "COALESCE(SUM(amount) FILTER (WHERE status='SUCCESS' AND transaction_type IN "
            "('INTERNAL_TRANSFER','INTERBANK_TRANSFER')),0) AS total_transfer_amount FROM transactions",
            {}, AdminTransactionReportRow,
        )
