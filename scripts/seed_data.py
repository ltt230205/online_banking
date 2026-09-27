"""Idempotent development seed for the initial banking schema."""

from datetime import date
from decimal import Decimal

from pwdlib import PasswordHash
from sqlalchemy import text

from app.config import settings
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
    password_hasher = PasswordHash.recommended()
    password_hashes = {
        "ADMIN": password_hasher.hash(settings.seed_admin_password.get_secret_value()),
        "EMPLOYEE": password_hasher.hash(settings.seed_employee_password.get_secret_value()),
        "CUSTOMER": password_hasher.hash(settings.seed_customer_password.get_secret_value()),
    }

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

        users = [
            ("admin", "admin@bank.local", "ADMIN"),
            ("employee", "employee@bank.local", "EMPLOYEE"),
            *[
                (f"customer{i}", f"customer{i}@bank.local", "CUSTOMER")
                for i in range(1, 21)
            ],
        ]
        for username, email, role in users:
            connection.execute(
                text(
                    "INSERT INTO users(role_id, username, email, password_hash, status) "
                    "SELECT id, :username, :email, :password_hash, 'ACTIVE' FROM roles WHERE name = :role "
                    "ON CONFLICT (username) DO UPDATE SET "
                    "role_id=EXCLUDED.role_id, email=EXCLUDED.email, password_hash=EXCLUDED.password_hash, "
                    "status='ACTIVE', is_deleted=false, deleted_at=NULL, deleted_by=NULL"
                ),
                {"username": username, "email": email, "password_hash": password_hashes[role], "role": role},
            )

        customer_names = {
            1: "Nguyễn Văn An",
            2: "Trần Thị Bình",
            3: "Lê Minh Cường",
            4: "Phạm Thu Dung",
            5: "Hoàng Quốc Huy",
            6: "Vũ Ngọc Lan",
            7: "Đặng Đức Minh",
            8: "Bùi Thanh Nga",
            9: "Đỗ Gia Phúc",
            10: "Ngô Khánh Quỳnh",
            11: "Dương Anh Sơn",
            12: "Lý Bảo Trang",
            13: "Mai Thành Trung",
            14: "Tạ Hải Yến",
            15: "Cao Nhật Nam",
            16: "Hồ Mỹ Linh",
            17: "Chu Đức Long",
            18: "Trịnh Hà My",
            19: "Đinh Tuấn Kiệt",
            20: "Lương Thảo Vy",
        }
        cities = ("Hà Nội", "Hải Phòng", "Đà Nẵng", "TP. Hồ Chí Minh", "Cần Thơ")
        customer_rows = [
            (
                f"customer{i}",
                f"CUS{i:06d}",
                customer_names[i],
                date(1988 + (i % 12), ((i - 1) % 12) + 1, ((i * 2 - 1) % 28) + 1),
                f"ID{i:09d}",
                f"090{i:07d}",
                cities[(i - 1) % len(cities)],
            )
            for i in range(1, 21)
        ]
        for username, code, full_name, dob, identity, phone, address in customer_rows:
            connection.execute(
                text(
                    "INSERT INTO customers(user_id, customer_code, full_name, date_of_birth, identity_number, phone, address, kyc_status, kyc_verified_at) "
                    "SELECT id, :code, :full_name, :dob, :identity, :phone, :address, 'VERIFIED', now() "
                    "FROM users WHERE username = :username ON CONFLICT (customer_code) DO NOTHING"
                ),
                {
                    "username": username,
                    "code": code,
                    "full_name": full_name,
                    "dob": dob,
                    "identity": identity,
                    "phone": phone,
                    "address": address,
                },
            )

        accounts = [
            (
                f"CUS{i:06d}",
                f"10000000{i:02d}",
                Decimal("20000000.0000")
                if i == 1
                else Decimal("10000000.0000")
                if i == 2
                else Decimal(5_000_000 + i * 750_000),
            )
            for i in range(1, 21)
        ]
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

        for i in range(1, 21):
            destination = i + 1 if i < 20 else 1
            owner_id = scalar(
                connection,
                "SELECT id FROM customers WHERE customer_code=:code",
                code=f"CUS{i:06d}",
            )
            linked_id = scalar(
                connection,
                "SELECT id FROM accounts WHERE account_number=:number",
                number=f"10000000{destination:02d}",
            )
            connection.execute(
                text(
                    "INSERT INTO payees(customer_id, nickname, account_number, account_name, bank_code, is_internal, linked_account_id) "
                    "VALUES (:customer_id, :nickname, :account_number, :account_name, 'LOCAL', true, :linked_id) "
                    "ON CONFLICT (customer_id, bank_code, account_number) DO NOTHING"
                ),
                {
                    "customer_id": owner_id,
                    "nickname": f"Người nhận {destination:02d}",
                    "account_number": f"10000000{destination:02d}",
                    "account_name": customer_names[destination],
                    "linked_id": linked_id,
                },
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

        invoice_types = (
            ("EVN", "ELECTRICITY"),
            ("SAWACO", "WATER"),
            ("VNPT", "INTERNET"),
            ("VIETTEL", "PHONE"),
        )
        for i in range(1, 21):
            customer_id = scalar(
                connection,
                "SELECT id FROM customers WHERE customer_code=:code",
                code=f"CUS{i:06d}",
            )
            user_id = scalar(
                connection,
                "SELECT id FROM users WHERE username=:username",
                username=f"customer{i}",
            )
            provider_code, service_type = invoice_types[(i - 1) % len(invoice_types)]
            connection.execute(
                text(
                    "INSERT INTO invoices(customer_id, invoice_code, provider_code, service_type, customer_reference, billing_period, amount, due_date, status) "
                    "VALUES (:customer_id, :invoice_code, :provider_code, :service_type, :reference, '2026-09', :amount, :due_date, 'UNPAID') "
                    "ON CONFLICT (invoice_code) DO NOTHING"
                ),
                {
                    "customer_id": customer_id,
                    "invoice_code": f"INV-SEED-{i:04d}",
                    "provider_code": provider_code,
                    "service_type": service_type,
                    "reference": f"REF{i:06d}",
                    "amount": Decimal(250_000 + i * 25_000),
                    "due_date": date(2026, 10, ((i - 1) % 20) + 5),
                },
            )
            connection.execute(
                text(
                    "INSERT INTO notifications(user_id, notification_type, event_type, title, content, status, is_read) "
                    "SELECT :user_id, 'IN_APP', 'WELCOME', 'Chào mừng', 'Tài khoản mẫu đã sẵn sàng.', 'SENT', false "
                    "WHERE NOT EXISTS (SELECT 1 FROM notifications WHERE user_id=:user_id AND event_type='WELCOME')"
                ),
                {"user_id": user_id},
            )

    print(
        "Seed completed: 20 customers with accounts, payees, invoices, "
        "notifications and sample transaction data."
    )


if __name__ == "__main__":
    seed()
