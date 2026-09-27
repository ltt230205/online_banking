"""Immutable values returned by raw-SQL repositories."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass(frozen=True)
class RoleRow:
    id: int
    name: str


@dataclass(frozen=True)
class UserCoreRow:
    id: int
    role_id: int
    username: str
    email: str
    password_hash: str
    status: str
    created_at: datetime
    last_login_at: datetime | None


@dataclass(frozen=True)
class UserRow(UserCoreRow):
    """JOIN users + roles, used for authorization and user responses."""

    role_name: str


@dataclass(frozen=True)
class CustomerRow:
    id: int
    user_id: int
    customer_code: str
    full_name: str
    date_of_birth: date
    identity_number: str
    phone: str
    address: str | None
    kyc_status: str
    kyc_verified_at: datetime | None
    version: int


@dataclass(frozen=True)
class AccountCoreRow:
    id: int
    customer_id: int
    account_number: str
    account_type: str
    balance: Decimal
    currency: str
    status: str
    version: int
    created_at: datetime


@dataclass(frozen=True)
class AccountRow(AccountCoreRow):
    """JOIN accounts + customers, including the statement display name."""

    customer_name: str


@dataclass(frozen=True)
class PayeeRow:
    id: int
    customer_id: int
    nickname: str
    account_number: str
    account_name: str
    bank_code: str
    is_internal: bool
    linked_account_id: int | None
    created_at: datetime


@dataclass(frozen=True)
class TransactionRow:
    id: int
    transaction_code: str
    transaction_type: str
    status: str
    source_account_id: int | None
    destination_account_id: int | None
    destination_account_number: str | None
    destination_bank_code: str | None
    destination_account_name: str | None
    amount: Decimal
    fee: Decimal
    currency: str
    description: str | None
    created_at: datetime
    completed_at: datetime | None


@dataclass(frozen=True)
class StatementRow:
    created_at: datetime
    transaction_code: str
    description: str | None
    entry_type: str
    amount: Decimal
    balance_before: Decimal
    balance_after: Decimal


@dataclass(frozen=True)
class InvoiceRow:
    id: int
    customer_id: int
    invoice_code: str
    provider_code: str
    service_type: str
    customer_reference: str
    billing_period: str | None
    amount: Decimal
    currency: str
    due_date: date
    status: str
    paid_at: datetime | None
    version: int


@dataclass(frozen=True)
class PaymentRow:
    id: int
    invoice_id: int
    account_id: int
    transaction_id: int
    amount: Decimal
    fee: Decimal
    status: str
    created_at: datetime
    completed_at: datetime | None


@dataclass(frozen=True)
class OtpRow:
    id: int
    user_id: int
    purpose: str
    code_hash: str
    transaction_id: int | None
    payment_id: int | None
    failed_attempts: int
    max_attempts: int
    expires_at: datetime
    consumed_at: datetime | None


@dataclass(frozen=True)
class AuditRow:
    id: int
    user_id: int | None
    action: str
    resource_type: str
    resource_id: str | None
    created_at: datetime


@dataclass(frozen=True)
class SummaryRow:
    total_balance: Decimal
    total_income: Decimal
    total_expense: Decimal
    transaction_count: int


@dataclass(frozen=True)
class CategoryExpenseRow:
    category: str
    amount: Decimal


@dataclass(frozen=True)
class MonthlyExpenseRow:
    month: str
    amount: Decimal


@dataclass(frozen=True)
class AdminTransactionReportRow:
    total_transactions: int
    successful_transactions: int
    failed_transactions: int
    total_transfer_amount: Decimal
