"""Idempotent development seed for the initial banking schema."""

import os
from datetime import date
from decimal import Decimal

from pwdlib import PasswordHash
from sqlalchemy import text

from app.db.session import engine


PERMISSIONS = [
    ("customers:read", "customers", "read"),
    ("customers:update", "customers", "update"),
    ("accounts:read", "accounts", "read"),
    ("transactions:read", "transactions", "read"),
    ("transfers:create", "transfers", "create"),
    ("payments:create", "payments", "create"),
    ("kyc:submit", "kyc", "submit"),
    ("kyc:approve", "kyc", "approve"),
    ("reports:read", "reports", "read"),
    ("reports:export", "reports", "export"),
    ("audit_logs:read", "audit_logs", "read"),
    ("users:manage", "users", "manage"),
    ("payees:manage", "payees", "manage"),
    ("notifications:read", "notifications", "read"),
]

ROLE_PERMISSIONS = {
    "ADMIN": [code for code, _, _ in PERMISSIONS],
    "EMPLOYEE": [
        "customers:read", "customers:update", "accounts:read", "transactions:read",
        "kyc:approve", "reports:read", "reports:export",
    ],
    "CUSTOMER": [
        "customers:read", "customers:update", "accounts:read", "transactions:read",
        "transfers:create", "payments:create", "kyc:submit", "reports:read",
        "reports:export", "payees:manage", "notifications:read",
    ],
}


def scalar(connection, sql: str, **params: object) -> int:
    return connection.execute(text(sql), params).scalar_one()


def seed() -> None:
    seed_password = os.getenv("SEED_DEFAULT_PASSWORD", "ChangeMe123!")
    password_hash = PasswordHash.recommended().hash(seed_password)

    with engine.begin() as connection:
        for role, description in (
            ("ADMIN", "Quản trị toàn hệ thống"),
            ("EMPLOYEE", "Nhân viên ngân hàng"),
            ("CUSTOMER", "Khách hàng"),
        ):
            connection.execute(
                text("INSERT INTO roles(name, description) VALUES (:name, :description) ON CONFLICT (name) DO NOTHING"),
                {"name": role, "description": description},
            )

        for code, resource, action in PERMISSIONS:
            connection.execute(
                text(
                    "INSERT INTO permissions(code, resource, action) VALUES (:code, :resource, :action) "
                    "ON CONFLICT (code) DO NOTHING"
                ),
                {"code": code, "resource": resource, "action": action},
            )

        for role, codes in ROLE_PERMISSIONS.items():
            connection.execute(
                text(
                    "INSERT INTO role_permissions(role_id, permission_id) "
                    "SELECT r.id, p.id FROM roles r CROSS JOIN permissions p "
                    "WHERE r.name = :role AND p.code = ANY(:codes) ON CONFLICT DO NOTHING"
                ),
                {"role": role, "codes": codes},
            )

        users = (
            ("admin", "admin@bank.local", "ADMIN"),
            ("employee", "employee@bank.local", "EMPLOYEE"),
            ("customer1", "customer1@bank.local", "CUSTOMER"),
            ("customer2", "customer2@bank.local", "CUSTOMER"),
        )
        for username, email, role in users:
            connection.execute(
                text(
                    "INSERT INTO users(role_id, username, email, password_hash, status) "
                    "SELECT id, :username, :email, :password_hash, 'ACTIVE' FROM roles WHERE name = :role "
                    "ON CONFLICT (username) DO NOTHING"
                ),
                {"username": username, "email": email, "password_hash": password_hash, "role": role},
            )

        customer_rows = (
            ("customer1", "CUS000001", "Nguyễn Văn An", date(1995, 5, 15), "ID000000001", "0900000001"),
            ("customer2", "CUS000002", "Trần Thị Bình", date(1993, 8, 20), "ID000000002", "0900000002"),
        )
        for username, code, full_name, dob, identity, phone in customer_rows:
            connection.execute(
                text(
                    "INSERT INTO customers(user_id, customer_code, full_name, date_of_birth, identity_number, phone, address, kyc_status, kyc_verified_at) "
                    "SELECT id, :code, :full_name, :dob, :identity, :phone, 'Hà Nội', 'VERIFIED', now() "
                    "FROM users WHERE username = :username ON CONFLICT (customer_code) DO NOTHING"
                ),
                {"username": username, "code": code, "full_name": full_name, "dob": dob, "identity": identity, "phone": phone},
            )

        accounts = (
            ("CUS000001", "1000000001", Decimal("20000000.0000")),
            ("CUS000002", "1000000002", Decimal("10000000.0000")),
        )
        for customer_code, number, balance in accounts:
            connection.execute(
                text(
                    "INSERT INTO accounts(customer_id, account_number, account_type, status, currency, balance) "
                    "SELECT id, :number, 'CHECKING', 'ACTIVE', 'VND', :balance FROM customers "
                    "WHERE customer_code = :customer_code ON CONFLICT (account_number) DO NOTHING"
                ),
                {"customer_code": customer_code, "number": number, "balance": balance},
            )

        customer1_id = scalar(connection, "SELECT id FROM customers WHERE customer_code='CUS000001'")
        account1_id = scalar(connection, "SELECT id FROM accounts WHERE account_number='1000000001'")
        account2_id = scalar(connection, "SELECT id FROM accounts WHERE account_number='1000000002'")
        user1_id = scalar(connection, "SELECT id FROM users WHERE username='customer1'")

        connection.execute(
            text(
                "INSERT INTO payees(customer_id, nickname, account_number, account_name, bank_code, is_internal, linked_account_id) "
                "VALUES (:customer_id, 'Bình', '1000000002', 'Trần Thị Bình', 'LOCAL', true, :linked_id) "
                "ON CONFLICT (customer_id, bank_code, account_number) DO NOTHING"
            ),
            {"customer_id": customer1_id, "linked_id": account2_id},
        )

        connection.execute(
            text(
                "INSERT INTO transactions(transaction_code, transaction_type, status, source_account_id, destination_account_id, amount, fee, currency, description, initiated_by, completed_at) "
                "VALUES ('TXN-SEED-0001', 'INTERNAL_TRANSFER', 'SUCCESS', :source, :destination, 1000000, 0, 'VND', 'Giao dịch mẫu', :user_id, now()) "
                "ON CONFLICT (transaction_code) DO NOTHING"
            ),
            {"source": account1_id, "destination": account2_id, "user_id": user1_id},
        )
        transaction_id = scalar(connection, "SELECT id FROM transactions WHERE transaction_code='TXN-SEED-0001'")
        connection.execute(
            text(
                "INSERT INTO transaction_entries(transaction_id, account_id, entry_type, amount, balance_before, balance_after) VALUES "
                "(:tx, :a1, 'DEBIT', 1000000, 21000000, 20000000), "
                "(:tx, :a2, 'CREDIT', 1000000, 9000000, 10000000) ON CONFLICT DO NOTHING"
            ),
            {"tx": transaction_id, "a1": account1_id, "a2": account2_id},
        )

        connection.execute(
            text(
                "INSERT INTO invoices(customer_id, invoice_code, provider_code, service_type, customer_reference, billing_period, amount, due_date, status) "
                "VALUES (:customer_id, 'INV-SEED-0001', 'EVN', 'ELECTRICITY', 'PE000001', '2026-09', 750000, '2026-10-10', 'UNPAID') "
                "ON CONFLICT (invoice_code) DO NOTHING"
            ),
            {"customer_id": customer1_id},
        )
        connection.execute(
            text(
                "INSERT INTO notifications(user_id, notification_type, event_type, title, content, status, is_read) "
                "SELECT :user_id, 'IN_APP', 'WELCOME', 'Chào mừng', 'Tài khoản mẫu đã sẵn sàng.', 'SENT', false "
                "WHERE NOT EXISTS (SELECT 1 FROM notifications WHERE user_id=:user_id AND event_type='WELCOME')"
            ),
            {"user_id": user1_id},
        )

    print("Seed completed: roles, permissions, users, customers, accounts and sample banking data.")


if __name__ == "__main__":
    seed()
