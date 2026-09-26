# Banking Management System — FastAPI Backend

Backend ngân hàng phục vụ bài tập lớn **Phát triển phần mềm hướng dịch vụ**. Hệ thống cung cấp JWT authentication, RBAC, KYC, tài khoản, chuyển khoản nội bộ/liên ngân hàng mock, OTP, hóa đơn, thanh toán, sao kê, báo cáo và audit log. Không có frontend.

## Công nghệ

- Python 3.12, FastAPI, Pydantic v2
- SQLAlchemy 2.x, PostgreSQL 17, Alembic
- PyJWT, OAuth2PasswordBearer, Argon2 password hashing
- pytest và FastAPI TestClient
- Docker Compose

## Kiến trúc

```text
Client → FastAPI Router → Service → Repository → SQLAlchemy → PostgreSQL
                            ├── OTP / Notification
                            ├── Audit
                            └── Mock Interbank Gateway
```

Router chỉ nhận/validate request, kiểm tra dependency và gọi service. Business rule, transaction boundary và orchestration nằm trong `app/services`; query persistence nằm trong `app/repositories`.

```text
app/
├── api/routers/       # HTTP endpoints
├── core/              # security, config, exceptions, database
├── models/            # SQLAlchemy entities
├── schemas/           # Pydantic request/response
├── repositories/      # database queries
├── services/          # business logic
├── db/                # engine/session/base
├── main.py
└── seed.py
```

Tài liệu chi tiết:

- [SRS](docs/SRS.md)
- [Use Cases](docs/USE_CASES.md)
- [Business Flows](docs/FLOWS.md)
- [ERD](docs/ERD.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Database Design](docs/DATABASE_DESIGN.md)
- [Database Dictionary](docs/DATABASE_DICTIONARY.md)

## Chạy bằng Docker

```powershell
Copy-Item .env.example .env
docker compose up --build -d
docker compose ps
```

Sau khi backend healthy:

- API: <http://localhost:8000>
- Swagger: <http://localhost:8000/docs>
- OpenAPI: <http://localhost:8000/openapi.json>
- Health: <http://localhost:8000/health>
- PostgreSQL từ máy host: `127.0.0.1:5433`

Container backend tự chạy `alembic upgrade head` trước khi khởi động Uvicorn.

## Cài đặt và chạy local

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
docker compose up -d db
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app.seed
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Không chạy đồng thời backend Docker và Uvicorn local trên cùng port 8000.

## Migration

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic current
.\.venv\Scripts\python.exe -m alembic check
```

Không dùng `Base.metadata.create_all()` cho production schema.

## Seed data

```powershell
.\.venv\Scripts\python.exe -m app.seed
```

Seed idempotent tạo 20 customer/accounts/payees/invoices/notifications cùng giao dịch ledger mẫu. Credential mặc định local:

| Role | Username | Password |
|---|---|---|
| ADMIN | `admin` | `Admin@123` |
| EMPLOYEE | `employee` | `Employee@123` |
| CUSTOMER | `customer1`…`customer20` | `Customer@123` |

Cả 20 customer có KYC VERIFIED. `customer1` và `customer2` lần lượt sở hữu account `1000000001` (20.000.000 VND) và `1000000002` (10.000.000 VND). Các credential này chỉ dành cho local demo.

## Authentication và Authorization

Login JSON:

```http
POST /api/v1/auth/login
Content-Type: application/json

{"username":"customer1","password":"Customer@123"}
```

JWT chứa `user_id`, `username`, `role`, `iat`, `exp`. Swagger Authorize dùng OAuth2 password endpoint ẩn `/api/v1/auth/token`. Password dùng Argon2; OTP dùng HMAC-SHA256 và database chỉ lưu hash.

RBAC:

- ADMIN: quản lý user/employee, customer, audit và báo cáo hệ thống.
- EMPLOYEE: xem customer và duyệt/từ chối KYC.
- CUSTOMER: chỉ truy cập tài nguyên thuộc chính mình và chỉ giao dịch khi KYC VERIFIED.

## API chính

| Nhóm | Endpoint |
|---|---|
| Auth | `POST /api/v1/auth/register`, `POST /api/v1/auth/login` |
| Customer/KYC | `GET /api/v1/customers/me`, `GET /api/v1/admin/customers`, `PUT /api/v1/admin/customers/{id}/kyc` |
| Account | `GET /api/v1/accounts`, `GET /api/v1/accounts/{id}`, `/balance`, `/statement` |
| Transfer | `POST /api/v1/transfers`, `POST /api/v1/transfers/{id}/verify-otp` |
| Transaction | `GET /api/v1/transactions` |
| Payee | `POST/GET /api/v1/payees`, `DELETE /api/v1/payees/{id}` |
| Invoice | `GET /api/v1/invoices`, `GET /api/v1/invoices/{id}` |
| Payment | `POST /api/v1/payments`, `POST /api/v1/payments/{id}/verify-otp` |
| Reports | `/api/v1/reports/me/summary`, `/expenses-by-category`, `/monthly-expenses` |
| Admin | `/api/v1/admin/users`, `/employees`, `/reports/transactions`, `/audit-logs` |

Danh sách transaction hỗ trợ `page`, `page_size`, `type`, `status`, `from_date`, `to_date`.

## Flow chuyển khoản

```text
POST /api/v1/transfers
  → validate customer + KYC
  → validate source/destination + balance
  → create PENDING transaction
  → generate OTP (6 số, 5 phút, tối đa 5 lần sai)
  → POST /api/v1/transfers/{id}/verify-otp
  → verify/consume OTP
  → BEGIN
  → SELECT accounts FOR UPDATE theo thứ tự ID
  → recheck status + balance
  → debit source / credit destination
  → insert ledger entries
  → transaction SUCCESS + audit + notification
  → COMMIT
```

Với `bank_code=OUR_BANK` hoặc `LOCAL`, tiền được chuyển giữa hai account trong PostgreSQL. Bank code khác dùng mock `InterbankGateway` và debit account nguồn nếu mock chấp nhận.

Trong `APP_ENV=development`, response bước tạo transfer/payment có `development_otp` để demo Swagger. Production không trả trường OTP này.

## Flow thanh toán hóa đơn

```text
POST /api/v1/payments
  → validate customer/KYC/invoice/account/balance
  → create payment + transaction PENDING
  → generate OTP
  → POST /api/v1/payments/{id}/verify-otp
  → lock account + invoice
  → recheck
  → debit + ledger entry
  → invoice PAID, payment/transaction SUCCESS
  → audit + notification + COMMIT
```

## Error response

```json
{
  "success": false,
  "error": {
    "code": "INSUFFICIENT_BALANCE",
    "message": "Account balance is insufficient"
  }
}
```

Các lỗi domain gồm `ACCOUNT_NOT_FOUND`, `ACCOUNT_LOCKED`, `INSUFFICIENT_BALANCE`, `KYC_NOT_VERIFIED`, `INVALID_OTP`, `OTP_EXPIRED`, `TRANSACTION_ALREADY_COMPLETED`, `INVOICE_ALREADY_PAID` và `PERMISSION_DENIED`.

## Test

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Test tự tạo database riêng `online_banking_test`, chạy Alembic và reset/seed trước từng case; database demo không bị thay đổi. Bộ test bao phủ register, login, balance, RBAC, transfer và hai số dư trước/sau, insufficient balance, KYC, OTP sai/hết hạn và bill payment.

## Dừng hệ thống

```powershell
docker compose down
```

Volume PostgreSQL vẫn được giữ. `docker compose down -v` sẽ xóa toàn bộ dữ liệu local và chỉ nên dùng khi chủ động reset database.
