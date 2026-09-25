# Kiến trúc hệ thống

Sơ đồ: [diagrams/architecture.mmd](diagrams/architecture.mmd).

## Phong cách kiến trúc

Hệ thống dùng **Modular Service-Oriented Architecture trong một FastAPI application** (modular monolith). Đây không phải microservice: triển khai một backend, dùng chung PostgreSQL, nhưng boundary nghiệp vụ rõ để dễ kiểm thử và có thể tách sau này nếu thật sự cần.

Luồng phụ thuộc:

```text
Client → FastAPI/Middleware → Router → Service → Repository → PostgreSQL
                                      ├→ Integration Adapter
                                      ├→ Audit Service
                                      └→ Celery/Redis → Worker
```

## Trách nhiệm các lớp

- **Router:** HTTP validation/mapping, dependency auth; không chứa nghiệp vụ.
- **Service:** transaction boundary, business rule, RBAC/ownership orchestration.
- **Repository:** query SQLAlchemy, row lock, pagination/filter allow-list; không quyết định nghiệp vụ.
- **Model:** persistence và constraint; **Schema:** request/response DTO tách khỏi ORM.
- **Adapter:** giao diện ổn định cho email/SMS/external bank; có mock cho bài tập.
- **Worker:** tác vụ chậm sau commit như email và export; nhận ID thay vì ORM object.

## Module mục tiêu

| Module | Trách nhiệm |
|---|---|
| Auth | password, access/refresh, reset, optional 2FA |
| Customer/KYC | profile, versioning, submit/review KYC |
| Account | account, balance read, status/lock |
| Transfer | internal/interbank orchestration, idempotency, ledger posting |
| Payment/Invoice | invoice lifecycle, atomic bill payment |
| OTP | generate random code, hash, expiry/attempt/consume |
| Report | aggregate ledger; statement/dashboard |
| Notification | persist notification, dispatch adapter |
| Audit | redaction và append audit event |
| Job | lifecycle export/import/background work |

## Transaction boundary và consistency

Service mở transaction. Transfer nội bộ khóa account theo ID tăng dần bằng `SELECT ... FOR UPDATE`, recheck balance rồi cập nhật hai balance, tạo ledger entries và đánh dấu SUCCESS trong một commit. Payment khóa account + invoice. Không gọi email trong transaction DB. Với gateway ngoài, dùng state PROCESSING và idempotency/reconciliation để xử lý dual-write; không thể có ACID xuyên hai hệ thống.

## Authentication và RBAC

Middleware/dependency xác minh access token; service kiểm tra permission `resource:action` và ownership. User có một role, role có nhiều permissions. Access token ngắn hạn; refresh/reset/OTP chỉ lưu hash. Permission deny-by-default và Employee không được nâng role ADMIN.

## Background job

API tạo row `jobs.PENDING` và enqueue sau khi DB commit. Celery dùng Redis làm broker; worker cập nhật PROCESSING/progress/result. File lớn nằm ở object/file storage, DB chỉ giữ location. Giai đoạn này chỉ thiết kế bảng và interface, chưa chạy Redis/Celery.

## External integration

- `EmailSender`/`SmsSender`: mock local, provider thật thay qua config.
- `ExternalBankGateway`: validate/send/query status, hỗ trợ idempotency key.
- Adapter có timeout, retry có giới hạn và mapping lỗi domain. Secret không vào log/audit.

## Triển khai và mở rộng

FastAPI stateless có thể nhân nhiều instance; worker scale độc lập. PostgreSQL là source of truth và cần connection pool, backup, migration tuần tự. Redis không giữ trạng thái tài chính. Correlation ID đi xuyên API/job/adapter để quan sát. Application log và audit log là hai luồng riêng.

## Cấu trúc dự kiến giai đoạn backend

```text
app/
  api/routers/
  core/                 # security, RBAC, logging
  models/               # ORM (đã có nền)
  schemas/
  repositories/
  services/
  integrations/
  workers/
  db/
```

Giai đoạn hiện tại không tạo router/service giả để tránh khiến skeleton bị hiểu nhầm là implementation hoàn chỉnh.
