from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class AccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_number: str
    account_type: str
    balance: Decimal
    currency: str
    status: str
    created_at: datetime


class BalanceResponse(BaseModel):
    account_number: str
    balance: Decimal
    currency: str


class StatementEntry(BaseModel):
    date: datetime
    transaction_code: str
    description: str | None
    debit: Decimal
    credit: Decimal
    balance: Decimal


class StatementResponse(BaseModel):
    account_number: str
    customer_name: str
    from_date: datetime
    to_date: datetime
    opening_balance: Decimal
    closing_balance: Decimal
    transactions: list[StatementEntry]
