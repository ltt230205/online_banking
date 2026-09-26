from decimal import Decimal

from pydantic import BaseModel


class SummaryResponse(BaseModel):
    total_balance: Decimal
    total_income: Decimal
    total_expense: Decimal
    transaction_count: int


class CategoryExpense(BaseModel):
    category: str
    amount: Decimal


class MonthlyExpense(BaseModel):
    month: str
    amount: Decimal


class AdminTransactionReport(BaseModel):
    total_transactions: int
    successful_transactions: int
    failed_transactions: int
    total_transfer_amount: Decimal
