from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


MONEY = Numeric(19, 4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SoftDeleteMixin:
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="RESTRICT"))


class Role(Base):
    __tablename__ = "roles"
    __table_args__ = (CheckConstraint("name IN ('ADMIN','EMPLOYEE','CUSTOMER')", name="valid_name"),)

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(30), unique=True)
    description: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Permission(Base):
    __tablename__ = "permissions"
    __table_args__ = (UniqueConstraint("resource", "action", name="uq_permissions_resource_action"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(100), unique=True)
    resource: Mapped[str] = mapped_column(String(50))
    action: Mapped[str] = mapped_column(String(30))
    description: Mapped[str | None] = mapped_column(String(255))


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id: Mapped[int] = mapped_column(
        SmallInteger, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
    permission_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True
    )


class User(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("status IN ('PENDING','ACTIVE','LOCKED','DISABLED')", name="valid_status"),
        Index("ix_users_active_username", "username", postgresql_where=text("is_deleted = false")),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    role_id: Mapped[int] = mapped_column(SmallInteger, ForeignKey("roles.id", ondelete="RESTRICT"))
    username: Mapped[str] = mapped_column(String(50), unique=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), server_default="PENDING")
    two_factor_enabled: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    role: Mapped[Role] = relationship()


class Customer(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "customers"
    __table_args__ = (
        CheckConstraint("kyc_status IN ('NOT_SUBMITTED','PENDING','VERIFIED','REJECTED')", name="valid_kyc_status"),
        CheckConstraint("version > 0", name="positive_version"),
        Index("ix_customers_kyc_status", "kyc_status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="RESTRICT"), unique=True)
    customer_code: Mapped[str] = mapped_column(String(30), unique=True)
    full_name: Mapped[str] = mapped_column(String(150))
    date_of_birth: Mapped[date] = mapped_column(Date)
    identity_number: Mapped[str] = mapped_column(String(30), unique=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True)
    address: Mapped[str | None] = mapped_column(Text)
    kyc_status: Mapped[str] = mapped_column(String(20), server_default="NOT_SUBMITTED")
    kyc_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, server_default="1")

    user: Mapped[User] = relationship(foreign_keys=[user_id])
    accounts: Mapped[list[Account]] = relationship(back_populates="customer")


class KycRequest(Base):
    __tablename__ = "kyc_requests"
    __table_args__ = (
        CheckConstraint("status IN ('PENDING','APPROVED','REJECTED')", name="valid_status"),
        Index("ix_kyc_requests_customer_status", "customer_id", "status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    customer_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("customers.id", ondelete="RESTRICT"))
    status: Mapped[str] = mapped_column(String(20), server_default="PENDING")
    document_data: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reviewed_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="RESTRICT"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[str | None] = mapped_column(Text)


class Account(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "accounts"
    __table_args__ = (
        CheckConstraint("account_type IN ('CHECKING','SAVINGS')", name="valid_type"),
        CheckConstraint("status IN ('ACTIVE','LOCKED','CLOSED')", name="valid_status"),
        CheckConstraint("balance >= 0", name="nonnegative_balance"),
        CheckConstraint("char_length(currency) = 3", name="currency_length"),
        CheckConstraint("version > 0", name="positive_version"),
        Index("ix_accounts_customer_status", "customer_id", "status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    customer_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("customers.id", ondelete="RESTRICT"))
    account_number: Mapped[str] = mapped_column(String(34), unique=True)
    account_type: Mapped[str] = mapped_column(String(20), server_default="CHECKING")
    status: Mapped[str] = mapped_column(String(20), server_default="ACTIVE")
    currency: Mapped[str] = mapped_column(String(3), server_default="VND")
    balance: Mapped[Decimal] = mapped_column(MONEY, server_default="0")
    version: Mapped[int] = mapped_column(Integer, server_default="1")

    customer: Mapped[Customer] = relationship(back_populates="accounts", foreign_keys=[customer_id])


class Payee(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "payees"
    __table_args__ = (
        UniqueConstraint("customer_id", "bank_code", "account_number", name="uq_payees_owner_bank_account"),
        CheckConstraint(
            "(is_internal = false) OR linked_account_id IS NOT NULL", name="internal_has_linked_account"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    customer_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("customers.id", ondelete="RESTRICT"))
    nickname: Mapped[str] = mapped_column(String(100))
    account_number: Mapped[str] = mapped_column(String(34))
    account_name: Mapped[str] = mapped_column(String(150))
    bank_code: Mapped[str] = mapped_column(String(20))
    is_internal: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    linked_account_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("accounts.id", ondelete="RESTRICT"))


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint(
            "transaction_type IN ('DEPOSIT','WITHDRAWAL','INTERNAL_TRANSFER','INTERBANK_TRANSFER','BILL_PAYMENT','FEE','REVERSAL')",
            name="valid_type",
        ),
        CheckConstraint("status IN ('PENDING','OTP_REQUIRED','PROCESSING','SUCCESS','FAILED','CANCELLED')", name="valid_status"),
        CheckConstraint("amount > 0", name="positive_amount"),
        CheckConstraint("fee >= 0", name="nonnegative_fee"),
        CheckConstraint("source_account_id IS NULL OR destination_account_id IS NULL OR source_account_id <> destination_account_id", name="different_accounts"),
        CheckConstraint("char_length(currency) = 3", name="currency_length"),
        Index("ix_transactions_source_created", "source_account_id", "created_at"),
        Index("ix_transactions_destination_created", "destination_account_id", "created_at"),
        Index("ix_transactions_status_created", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    transaction_code: Mapped[str] = mapped_column(String(40), unique=True)
    transaction_type: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(20), server_default="PENDING")
    source_account_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("accounts.id", ondelete="RESTRICT"))
    destination_account_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("accounts.id", ondelete="RESTRICT"))
    destination_account_number: Mapped[str | None] = mapped_column(String(34))
    destination_bank_code: Mapped[str | None] = mapped_column(String(20))
    destination_account_name: Mapped[str | None] = mapped_column(String(150))
    amount: Mapped[Decimal] = mapped_column(MONEY)
    fee: Mapped[Decimal] = mapped_column(MONEY, server_default="0")
    currency: Mapped[str] = mapped_column(String(3), server_default="VND")
    description: Mapped[str | None] = mapped_column(String(500))
    idempotency_key: Mapped[str | None] = mapped_column(String(100), unique=True)
    failure_code: Mapped[str | None] = mapped_column(String(50))
    failure_reason: Mapped[str | None] = mapped_column(String(500))
    initiated_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    entries: Mapped[list[TransactionEntry]] = relationship(back_populates="transaction")


class TransactionEntry(Base):
    __tablename__ = "transaction_entries"
    __table_args__ = (
        CheckConstraint("entry_type IN ('DEBIT','CREDIT')", name="valid_type"),
        CheckConstraint("amount > 0", name="positive_amount"),
        CheckConstraint("balance_before >= 0 AND balance_after >= 0", name="nonnegative_balances"),
        CheckConstraint(
            "(entry_type = 'DEBIT' AND balance_after = balance_before - amount) OR "
            "(entry_type = 'CREDIT' AND balance_after = balance_before + amount)",
            name="balance_arithmetic",
        ),
        UniqueConstraint("transaction_id", "account_id", "entry_type", name="uq_transaction_entries_tx_account_type"),
        Index("ix_transaction_entries_account_created", "account_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    transaction_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("transactions.id", ondelete="RESTRICT"))
    account_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("accounts.id", ondelete="RESTRICT"))
    entry_type: Mapped[str] = mapped_column(String(10))
    amount: Mapped[Decimal] = mapped_column(MONEY)
    balance_before: Mapped[Decimal] = mapped_column(MONEY)
    balance_after: Mapped[Decimal] = mapped_column(MONEY)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    transaction: Mapped[Transaction] = relationship(back_populates="entries")


class Invoice(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "invoices"
    __table_args__ = (
        CheckConstraint("service_type IN ('ELECTRICITY','WATER','INTERNET','PHONE')", name="valid_service_type"),
        CheckConstraint("status IN ('UNPAID','PENDING','PAID','OVERDUE','CANCELLED')", name="valid_status"),
        CheckConstraint("amount > 0", name="positive_amount"),
        CheckConstraint("version > 0", name="positive_version"),
        CheckConstraint("char_length(currency) = 3", name="currency_length"),
        Index("ix_invoices_customer_status", "customer_id", "status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    customer_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("customers.id", ondelete="RESTRICT"))
    invoice_code: Mapped[str] = mapped_column(String(50), unique=True)
    provider_code: Mapped[str] = mapped_column(String(30))
    service_type: Mapped[str] = mapped_column(String(20))
    customer_reference: Mapped[str] = mapped_column(String(50))
    billing_period: Mapped[str | None] = mapped_column(String(20))
    amount: Mapped[Decimal] = mapped_column(MONEY)
    currency: Mapped[str] = mapped_column(String(3), server_default="VND")
    due_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), server_default="UNPAID")
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, server_default="1")


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("status IN ('PENDING','OTP_REQUIRED','PROCESSING','SUCCESS','FAILED','CANCELLED')", name="valid_status"),
        CheckConstraint("amount > 0", name="positive_amount"),
        CheckConstraint("fee >= 0", name="nonnegative_fee"),
        Index("ix_payments_account_created", "account_id", "created_at"),
        Index(
            "uq_payments_successful_invoice",
            "invoice_id",
            unique=True,
            postgresql_where=text("status = 'SUCCESS'"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    payment_code: Mapped[str] = mapped_column(String(40), unique=True)
    invoice_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("invoices.id", ondelete="RESTRICT"))
    account_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("accounts.id", ondelete="RESTRICT"))
    transaction_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("transactions.id", ondelete="RESTRICT"), unique=True)
    amount: Mapped[Decimal] = mapped_column(MONEY)
    fee: Mapped[Decimal] = mapped_column(MONEY, server_default="0")
    status: Mapped[str] = mapped_column(String(20), server_default="PENDING")
    failure_reason: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OtpCode(Base):
    __tablename__ = "otp_codes"
    __table_args__ = (
        CheckConstraint("purpose IN ('LOGIN_2FA','TRANSFER','BILL_PAYMENT','PASSWORD_RESET')", name="valid_purpose"),
        CheckConstraint("failed_attempts >= 0 AND failed_attempts <= max_attempts", name="valid_attempts"),
        CheckConstraint("max_attempts > 0", name="positive_max_attempts"),
        CheckConstraint("expires_at > created_at", name="valid_expiry"),
        CheckConstraint("num_nonnulls(transaction_id, payment_id) <= 1", name="single_business_target"),
        Index("ix_otp_codes_user_purpose_created", "user_id", "purpose", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="RESTRICT"))
    purpose: Mapped[str] = mapped_column(String(30))
    code_hash: Mapped[str] = mapped_column(String(255))
    transaction_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("transactions.id", ondelete="RESTRICT"))
    payment_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("payments.id", ondelete="RESTRICT"))
    failed_attempts: Mapped[int] = mapped_column(SmallInteger, server_default="0")
    max_attempts: Mapped[int] = mapped_column(SmallInteger, server_default="5")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = (Index("ix_refresh_tokens_user_expires", "user_id", "expires_at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="RESTRICT"))
    token_hash: Mapped[str] = mapped_column(String(255), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    __table_args__ = (Index("ix_password_reset_tokens_user_expires", "user_id", "expires_at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="RESTRICT"))
    token_hash: Mapped[str] = mapped_column(String(255), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint("notification_type IN ('EMAIL','IN_APP')", name="valid_type"),
        CheckConstraint("status IN ('PENDING','SENT','FAILED','READ')", name="valid_status"),
        Index("ix_notifications_user_read_created", "user_id", "is_read", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="RESTRICT"))
    notification_type: Mapped[str] = mapped_column(String(20))
    event_type: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), server_default="PENDING")
    is_read: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_user_created", "user_id", "created_at"),
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
        Index("ix_audit_logs_action_created", "action", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="RESTRICT"))
    action: Mapped[str] = mapped_column(String(60))
    resource_type: Mapped[str] = mapped_column(String(60))
    resource_id: Mapped[str | None] = mapped_column(String(100))
    before_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    after_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    ip_address: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None] = mapped_column(String(500))
    correlation_id: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint("status IN ('PENDING','PROCESSING','SUCCESS','FAILED')", name="valid_status"),
        CheckConstraint("progress >= 0 AND progress <= 100", name="valid_progress"),
        Index("ix_jobs_status_created", "status", "created_at"),
        Index("ix_jobs_requested_by_created", "requested_by", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    job_type: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20), server_default="PENDING")
    requested_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="RESTRICT"))
    parameters: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    result_location: Mapped[str | None] = mapped_column(String(500))
    error_message: Mapped[str | None] = mapped_column(Text)
    progress: Mapped[int] = mapped_column(SmallInteger, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
