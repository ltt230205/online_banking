"""Initial Banking Schema.

Revision ID: 20260925_0001
Revises: None
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20260925_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SCHEMA_SQL = r"""
CREATE TABLE roles (
    id SMALLSERIAL PRIMARY KEY,
    name VARCHAR(30) NOT NULL CONSTRAINT uq_roles_name UNIQUE,
    description VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_roles_valid_name CHECK (name IN ('ADMIN','EMPLOYEE','CUSTOMER'))
);

CREATE TABLE permissions (
    id SERIAL PRIMARY KEY,
    code VARCHAR(100) NOT NULL CONSTRAINT uq_permissions_code UNIQUE,
    resource VARCHAR(50) NOT NULL,
    action VARCHAR(30) NOT NULL,
    description VARCHAR(255),
    CONSTRAINT uq_permissions_resource_action UNIQUE (resource, action)
);

CREATE TABLE role_permissions (
    role_id SMALLINT NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id INTEGER NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    role_id SMALLINT NOT NULL REFERENCES roles(id) ON DELETE RESTRICT,
    username VARCHAR(50) NOT NULL CONSTRAINT uq_users_username UNIQUE,
    email VARCHAR(255) NOT NULL CONSTRAINT uq_users_email UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    two_factor_enabled BOOLEAN NOT NULL DEFAULT false,
    last_login_at TIMESTAMPTZ,
    is_deleted BOOLEAN NOT NULL DEFAULT false,
    deleted_at TIMESTAMPTZ,
    deleted_by BIGINT REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_users_valid_status CHECK (status IN ('PENDING','ACTIVE','LOCKED','DISABLED'))
);
CREATE INDEX ix_users_active_username ON users(username) WHERE is_deleted = false;

CREATE TABLE customers (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL CONSTRAINT uq_customers_user_id UNIQUE REFERENCES users(id) ON DELETE RESTRICT,
    customer_code VARCHAR(30) NOT NULL CONSTRAINT uq_customers_customer_code UNIQUE,
    full_name VARCHAR(150) NOT NULL,
    date_of_birth DATE NOT NULL,
    identity_number VARCHAR(30) NOT NULL CONSTRAINT uq_customers_identity_number UNIQUE,
    phone VARCHAR(20) NOT NULL CONSTRAINT uq_customers_phone UNIQUE,
    address TEXT,
    kyc_status VARCHAR(20) NOT NULL DEFAULT 'NOT_SUBMITTED',
    kyc_verified_at TIMESTAMPTZ,
    version INTEGER NOT NULL DEFAULT 1,
    is_deleted BOOLEAN NOT NULL DEFAULT false,
    deleted_at TIMESTAMPTZ,
    deleted_by BIGINT REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_customers_valid_kyc_status CHECK (kyc_status IN ('NOT_SUBMITTED','PENDING','VERIFIED','REJECTED')),
    CONSTRAINT ck_customers_positive_version CHECK (version > 0)
);
CREATE INDEX ix_customers_kyc_status ON customers(kyc_status);

CREATE TABLE kyc_requests (
    id BIGSERIAL PRIMARY KEY,
    customer_id BIGINT NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    document_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    reviewed_by BIGINT REFERENCES users(id) ON DELETE RESTRICT,
    reviewed_at TIMESTAMPTZ,
    rejection_reason TEXT,
    CONSTRAINT ck_kyc_requests_valid_status CHECK (status IN ('PENDING','APPROVED','REJECTED'))
);
CREATE INDEX ix_kyc_requests_customer_status ON kyc_requests(customer_id, status);

CREATE TABLE accounts (
    id BIGSERIAL PRIMARY KEY,
    customer_id BIGINT NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
    account_number VARCHAR(34) NOT NULL CONSTRAINT uq_accounts_account_number UNIQUE,
    account_type VARCHAR(20) NOT NULL DEFAULT 'CHECKING',
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    currency VARCHAR(3) NOT NULL DEFAULT 'VND',
    balance NUMERIC(19,4) NOT NULL DEFAULT 0,
    version INTEGER NOT NULL DEFAULT 1,
    is_deleted BOOLEAN NOT NULL DEFAULT false,
    deleted_at TIMESTAMPTZ,
    deleted_by BIGINT REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_accounts_valid_type CHECK (account_type IN ('CHECKING','SAVINGS')),
    CONSTRAINT ck_accounts_valid_status CHECK (status IN ('ACTIVE','LOCKED','CLOSED')),
    CONSTRAINT ck_accounts_nonnegative_balance CHECK (balance >= 0),
    CONSTRAINT ck_accounts_currency_length CHECK (char_length(currency) = 3),
    CONSTRAINT ck_accounts_positive_version CHECK (version > 0)
);
CREATE INDEX ix_accounts_customer_status ON accounts(customer_id, status);

CREATE TABLE payees (
    id BIGSERIAL PRIMARY KEY,
    customer_id BIGINT NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
    nickname VARCHAR(100) NOT NULL,
    account_number VARCHAR(34) NOT NULL,
    account_name VARCHAR(150) NOT NULL,
    bank_code VARCHAR(20) NOT NULL,
    is_internal BOOLEAN NOT NULL DEFAULT false,
    linked_account_id BIGINT REFERENCES accounts(id) ON DELETE RESTRICT,
    is_deleted BOOLEAN NOT NULL DEFAULT false,
    deleted_at TIMESTAMPTZ,
    deleted_by BIGINT REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_payees_owner_bank_account UNIQUE (customer_id, bank_code, account_number),
    CONSTRAINT ck_payees_internal_has_linked_account CHECK ((is_internal = false) OR linked_account_id IS NOT NULL)
);

CREATE TABLE transactions (
    id BIGSERIAL PRIMARY KEY,
    transaction_code VARCHAR(40) NOT NULL CONSTRAINT uq_transactions_transaction_code UNIQUE,
    transaction_type VARCHAR(30) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    source_account_id BIGINT REFERENCES accounts(id) ON DELETE RESTRICT,
    destination_account_id BIGINT REFERENCES accounts(id) ON DELETE RESTRICT,
    destination_account_number VARCHAR(34),
    destination_bank_code VARCHAR(20),
    destination_account_name VARCHAR(150),
    amount NUMERIC(19,4) NOT NULL,
    fee NUMERIC(19,4) NOT NULL DEFAULT 0,
    currency VARCHAR(3) NOT NULL DEFAULT 'VND',
    description VARCHAR(500),
    idempotency_key VARCHAR(100) CONSTRAINT uq_transactions_idempotency_key UNIQUE,
    failure_code VARCHAR(50),
    failure_reason VARCHAR(500),
    initiated_by BIGINT REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    CONSTRAINT ck_transactions_valid_type CHECK (transaction_type IN ('DEPOSIT','WITHDRAWAL','INTERNAL_TRANSFER','INTERBANK_TRANSFER','BILL_PAYMENT','FEE','REVERSAL')),
    CONSTRAINT ck_transactions_valid_status CHECK (status IN ('PENDING','OTP_REQUIRED','PROCESSING','SUCCESS','FAILED','CANCELLED')),
    CONSTRAINT ck_transactions_positive_amount CHECK (amount > 0),
    CONSTRAINT ck_transactions_nonnegative_fee CHECK (fee >= 0),
    CONSTRAINT ck_transactions_different_accounts CHECK (source_account_id IS NULL OR destination_account_id IS NULL OR source_account_id <> destination_account_id),
    CONSTRAINT ck_transactions_currency_length CHECK (char_length(currency) = 3)
);
CREATE INDEX ix_transactions_source_created ON transactions(source_account_id, created_at);
CREATE INDEX ix_transactions_destination_created ON transactions(destination_account_id, created_at);
CREATE INDEX ix_transactions_status_created ON transactions(status, created_at);

CREATE TABLE transaction_entries (
    id BIGSERIAL PRIMARY KEY,
    transaction_id BIGINT NOT NULL REFERENCES transactions(id) ON DELETE RESTRICT,
    account_id BIGINT NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT,
    entry_type VARCHAR(10) NOT NULL,
    amount NUMERIC(19,4) NOT NULL,
    balance_before NUMERIC(19,4) NOT NULL,
    balance_after NUMERIC(19,4) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_transaction_entries_valid_type CHECK (entry_type IN ('DEBIT','CREDIT')),
    CONSTRAINT ck_transaction_entries_positive_amount CHECK (amount > 0),
    CONSTRAINT ck_transaction_entries_nonnegative_balances CHECK (balance_before >= 0 AND balance_after >= 0),
    CONSTRAINT ck_transaction_entries_balance_arithmetic CHECK ((entry_type = 'DEBIT' AND balance_after = balance_before - amount) OR (entry_type = 'CREDIT' AND balance_after = balance_before + amount)),
    CONSTRAINT uq_transaction_entries_tx_account_type UNIQUE (transaction_id, account_id, entry_type)
);
CREATE INDEX ix_transaction_entries_account_created ON transaction_entries(account_id, created_at);

CREATE TABLE invoices (
    id BIGSERIAL PRIMARY KEY,
    customer_id BIGINT NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
    invoice_code VARCHAR(50) NOT NULL CONSTRAINT uq_invoices_invoice_code UNIQUE,
    provider_code VARCHAR(30) NOT NULL,
    service_type VARCHAR(20) NOT NULL,
    customer_reference VARCHAR(50) NOT NULL,
    billing_period VARCHAR(20),
    amount NUMERIC(19,4) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'VND',
    due_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'UNPAID',
    paid_at TIMESTAMPTZ,
    version INTEGER NOT NULL DEFAULT 1,
    is_deleted BOOLEAN NOT NULL DEFAULT false,
    deleted_at TIMESTAMPTZ,
    deleted_by BIGINT REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_invoices_valid_service_type CHECK (service_type IN ('ELECTRICITY','WATER','INTERNET','PHONE')),
    CONSTRAINT ck_invoices_valid_status CHECK (status IN ('UNPAID','PENDING','PAID','OVERDUE','CANCELLED')),
    CONSTRAINT ck_invoices_positive_amount CHECK (amount > 0),
    CONSTRAINT ck_invoices_positive_version CHECK (version > 0),
    CONSTRAINT ck_invoices_currency_length CHECK (char_length(currency) = 3)
);
CREATE INDEX ix_invoices_customer_status ON invoices(customer_id, status);

CREATE TABLE payments (
    id BIGSERIAL PRIMARY KEY,
    payment_code VARCHAR(40) NOT NULL CONSTRAINT uq_payments_payment_code UNIQUE,
    invoice_id BIGINT NOT NULL REFERENCES invoices(id) ON DELETE RESTRICT,
    account_id BIGINT NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT,
    transaction_id BIGINT CONSTRAINT uq_payments_transaction_id UNIQUE REFERENCES transactions(id) ON DELETE RESTRICT,
    amount NUMERIC(19,4) NOT NULL,
    fee NUMERIC(19,4) NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    failure_reason VARCHAR(500),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    CONSTRAINT ck_payments_valid_status CHECK (status IN ('PENDING','OTP_REQUIRED','PROCESSING','SUCCESS','FAILED','CANCELLED')),
    CONSTRAINT ck_payments_positive_amount CHECK (amount > 0),
    CONSTRAINT ck_payments_nonnegative_fee CHECK (fee >= 0)
);
CREATE INDEX ix_payments_account_created ON payments(account_id, created_at);
CREATE UNIQUE INDEX uq_payments_successful_invoice ON payments(invoice_id) WHERE status = 'SUCCESS';

CREATE TABLE otp_codes (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    purpose VARCHAR(30) NOT NULL,
    code_hash VARCHAR(255) NOT NULL,
    transaction_id BIGINT REFERENCES transactions(id) ON DELETE RESTRICT,
    payment_id BIGINT REFERENCES payments(id) ON DELETE RESTRICT,
    failed_attempts SMALLINT NOT NULL DEFAULT 0,
    max_attempts SMALLINT NOT NULL DEFAULT 5,
    expires_at TIMESTAMPTZ NOT NULL,
    consumed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_otp_codes_valid_purpose CHECK (purpose IN ('LOGIN_2FA','TRANSFER','BILL_PAYMENT','PASSWORD_RESET')),
    CONSTRAINT ck_otp_codes_valid_attempts CHECK (failed_attempts >= 0 AND failed_attempts <= max_attempts),
    CONSTRAINT ck_otp_codes_positive_max_attempts CHECK (max_attempts > 0),
    CONSTRAINT ck_otp_codes_valid_expiry CHECK (expires_at > created_at),
    CONSTRAINT ck_otp_codes_single_business_target CHECK (num_nonnulls(transaction_id, payment_id) <= 1)
);
CREATE INDEX ix_otp_codes_user_purpose_created ON otp_codes(user_id, purpose, created_at);

CREATE TABLE refresh_tokens (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    token_hash VARCHAR(255) NOT NULL CONSTRAINT uq_refresh_tokens_token_hash UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_refresh_tokens_user_expires ON refresh_tokens(user_id, expires_at);

CREATE TABLE password_reset_tokens (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    token_hash VARCHAR(255) NOT NULL CONSTRAINT uq_password_reset_tokens_token_hash UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_password_reset_tokens_user_expires ON password_reset_tokens(user_id, expires_at);

CREATE TABLE notifications (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    notification_type VARCHAR(20) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    is_read BOOLEAN NOT NULL DEFAULT false,
    read_at TIMESTAMPTZ,
    sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_notifications_valid_type CHECK (notification_type IN ('EMAIL','IN_APP')),
    CONSTRAINT ck_notifications_valid_status CHECK (status IN ('PENDING','SENT','FAILED','READ'))
);
CREATE INDEX ix_notifications_user_read_created ON notifications(user_id, is_read, created_at);

CREATE TABLE audit_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE RESTRICT,
    action VARCHAR(60) NOT NULL,
    resource_type VARCHAR(60) NOT NULL,
    resource_id VARCHAR(100),
    before_data JSONB,
    after_data JSONB,
    ip_address INET,
    user_agent VARCHAR(500),
    correlation_id VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_audit_logs_user_created ON audit_logs(user_id, created_at);
CREATE INDEX ix_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX ix_audit_logs_action_created ON audit_logs(action, created_at);

CREATE TABLE jobs (
    id BIGSERIAL PRIMARY KEY,
    job_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    requested_by BIGINT REFERENCES users(id) ON DELETE RESTRICT,
    parameters JSONB NOT NULL DEFAULT '{}'::jsonb,
    result_location VARCHAR(500),
    error_message TEXT,
    progress SMALLINT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    CONSTRAINT ck_jobs_valid_status CHECK (status IN ('PENDING','PROCESSING','SUCCESS','FAILED')),
    CONSTRAINT ck_jobs_valid_progress CHECK (progress >= 0 AND progress <= 100)
);
CREATE INDEX ix_jobs_status_created ON jobs(status, created_at);
CREATE INDEX ix_jobs_requested_by_created ON jobs(requested_by, created_at);
"""


def upgrade() -> None:
    op.execute(SCHEMA_SQL)


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS jobs, audit_logs, notifications, password_reset_tokens,
            refresh_tokens, otp_codes, payments, invoices, transaction_entries,
            transactions, payees, accounts, kyc_requests, customers, users,
            role_permissions, permissions, roles CASCADE;
        """
    )
