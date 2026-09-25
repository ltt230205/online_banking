# Banking Management System

Nền móng giai đoạn 1 cho bài tập lớn **Phát triển phần mềm hướng dịch vụ**: phân tích yêu cầu, SRS, use case, flow, ERD, kiến trúc, PostgreSQL schema, SQLAlchemy models, Alembic migration và seed data.

> Giai đoạn này chưa triển khai FastAPI router, JWT, transfer/payment service, Celery, export file hoặc frontend. `app/main.py` chỉ là skeleton/healthcheck có sẵn từ ban đầu.

## Requirements

- Python 3.12
- Docker Desktop với Linux containers
- PostgreSQL 17 chạy bằng Docker Compose

## Architecture

Kiến trúc mục tiêu là modular service-oriented architecture trong một FastAPI application:

```text
Client → FastAPI/Auth/RBAC → Router → Service → Repository → PostgreSQL
                                      ├→ External adapters
                                      └→ Celery → Redis/Worker
```

Chi tiết: [SRS](docs/SRS.md), [Use Cases](docs/USE_CASES.md), [Flows](docs/FLOWS.md), [Architecture](docs/ARCHITECTURE.md).

## Database và ERD

PostgreSQL dùng `NUMERIC(19,4)` cho tiền, `VARCHAR + CHECK` cho lifecycle, soft-delete trên master data, optimistic `version`, audit log riêng và ledger `transaction_entries` phục vụ sao kê.

- [ERD và quyết định thiết kế](docs/ERD.md)
- [Data dictionary và transaction safety](docs/DATABASE_DESIGN.md)
- [Mermaid ERD](docs/diagrams/erd.mmd)

## Cài môi trường Python

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Tạo `.env` nếu chưa có:

```powershell
Copy-Item .env.example .env
```

Các giá trị trong `.env.example` chỉ dành cho local. Đổi `POSTGRES_PASSWORD` và `SEED_DEFAULT_PASSWORD` ở môi trường khác.

## Khởi động PostgreSQL

Compose ở giai đoạn 1 chỉ chạy database:

```powershell
docker compose up -d db
docker compose ps
docker compose logs -f db
```

PostgreSQL bind tại `127.0.0.1:5433` theo cấu hình mặc định và lưu dữ liệu trong volume `postgres_data`.

## Chạy migration

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic current
```

Rollback schema ban đầu trong database local dùng `alembic downgrade base`; thao tác này xóa các bảng nên không dùng khi cần giữ dữ liệu.

## Seed database

```powershell
$env:SEED_DEFAULT_PASSWORD = "mật-khẩu-local-của-bạn"
.\.venv\Scripts\python.exe -m scripts.seed_data
Remove-Item Env:SEED_DEFAULT_PASSWORD
```

Nếu không đặt biến, script dùng password mẫu trong `.env.example`. Script seed idempotent và database chỉ nhận password hash Argon2.

Seed gồm:

- Roles `ADMIN`, `EMPLOYEE`, `CUSTOMER`, permissions và role mappings.
- Users `admin`, `employee`, `customer1`, `customer2`.
- Hai customer KYC VERIFIED.
- Account `1000000001` có 20.000.000 VND và `1000000002` có 10.000.000 VND.
- Payee, invoice, giao dịch nội bộ cùng ledger entries và notification mẫu.

## Kiểm tra

```powershell
.\.venv\Scripts\python.exe -m compileall -q app scripts alembic
.\.venv\Scripts\python.exe -m alembic check
docker compose exec db psql -U banking -d online_banking -c "\dt"
```

`alembic check` phải báo không có operation mới nếu ORM models và migration đồng bộ.

## Tắt database

```powershell
docker compose down
```

Lệnh trên giữ volume. Chỉ dùng `docker compose down -v` nếu chủ động muốn xóa toàn bộ dữ liệu local.

## Giai đoạn tiếp theo

Sau khi thiết kế được duyệt: tạo schemas/repositories/services/routers; triển khai JWT rotation, RBAC/ownership, OTP, transaction locking, adapters mock, Celery/Redis, test tự động và export. Không đưa nghiệp vụ vào router.
