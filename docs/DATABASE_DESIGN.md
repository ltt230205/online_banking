# Thiết kế cơ sở dữ liệu

## Quy ước chung

- PostgreSQL; tên bảng số nhiều và `snake_case`; PK `id`; FK `<entity>_id`.
- ID dùng `BIGSERIAL` cho dữ liệu nghiệp vụ, `SERIAL/SMALLSERIAL` cho catalog nhỏ.
- Thời gian dùng `TIMESTAMPTZ`, tiền `NUMERIC(19,4)`, dữ liệu linh hoạt có kiểm soát dùng `JSONB`.
- Lifecycle dùng `VARCHAR + CHECK` để migration dễ hơn PostgreSQL ENUM.
- FK lịch sử dùng `ON DELETE RESTRICT`; chỉ bảng nối RBAC dùng CASCADE.

## Data dictionary

Ký hiệu: PK = primary key, FK = foreign key, UK = unique, CK = check.

### `roles`

Mục đích: ba vai trò hệ thống. Cột: `id SMALLINT` PK, `name VARCHAR(30)` UK/CK ADMIN|EMPLOYEE|CUSTOMER, `description`, `created_at`. Quan hệ 1:N users và M:N permissions.

### `permissions`

Mục đích: quyền dạng resource:action. Cột: `id INTEGER` PK, `code VARCHAR(100)` UK, `resource VARCHAR(50)`, `action VARCHAR(30)`, `description`; UK `(resource, action)`. Quan hệ M:N roles.

### `role_permissions`

Mục đích: bảng nối RBAC. PK ghép `role_id SMALLINT` + `permission_id INTEGER`, đồng thời là FK; CASCADE chỉ áp dụng cho catalog mapping.

### `users`

Mục đích: định danh đăng nhập cho mọi role. Cột chính: `role_id` FK, `username VARCHAR(50)` UK, `email VARCHAR(255)` UK, `password_hash`, status CK, 2FA, last login, timestamps và soft-delete (`is_deleted/deleted_at/deleted_by`). Index partial username active hỗ trợ login. Không lưu password/token plaintext.

### `customers`

Mục đích: hồ sơ nghiệp vụ chỉ dành cho CUSTOMER. `user_id` FK+UK tạo quan hệ 1–0/1; `customer_code`, `identity_number`, `phone` UK; thông tin cá nhân; `kyc_status` CK; verified time; `version > 0`; timestamps/soft-delete. Index KYC status. Dữ liệu nhạy cảm cần kiểm soát field-level trong backend.

### `kyc_requests`

Mục đích: lịch sử lần nộp/xét KYC. Cột: customer FK, status CK, `document_data JSONB`, submitted/reviewed timestamps, `reviewed_by` FK, rejection reason. Index `(customer_id,status)`. JSONB chỉ giữ metadata/location, không lưu binary file.

### `accounts`

Mục đích: tài khoản và số dư hiện hành. Cột: customer FK, `account_number VARCHAR(34)` UK, type/status CK, currency 3 ký tự, `balance NUMERIC(19,4) >= 0`, `version > 0`, timestamps/soft-delete. Index `(customer_id,status)`. Mọi thay đổi balance phải kèm ledger entry trong cùng DB transaction.

### `payees`

Mục đích: người thụ hưởng của customer. Cột: owner customer FK, nickname, account/bank/name snapshot, `is_internal`, optional `linked_account_id` FK, timestamps/soft-delete. UK `(customer_id,bank_code,account_number)`; CK internal phải có linked account.

### `transactions`

Mục đích: lệnh/lifecycle giao dịch tài chính, không phải audit. Cột: `transaction_code` UK, type/status CK, source/destination account FK nullable, snapshot destination ngoài, amount > 0, fee >= 0, currency, description, `idempotency_key` UK nullable, failure data, actor, created/completed. CK hai account khác nhau. Index source+time, destination+time, status+time. Không bao giờ DELETE; sửa sai bằng FAILED/CANCELLED/REVERSAL.

### `transaction_entries`

Mục đích: ledger theo account và nguồn sao kê. Cột: transaction/account FK, entry type DEBIT|CREDIT, amount > 0, `balance_before/after >= 0`, created_at. CK bảo đảm phép cộng/trừ; UK transaction+account+type; index account+time. Không update/delete sau khi post; correction dùng reversal.

### `invoices`

Mục đích: hóa đơn dịch vụ. Cột: customer FK, `invoice_code` UK, provider/service/customer reference, billing period, amount > 0, currency, due date, status CK, paid time, `version > 0`, timestamps/soft-delete. Index `(customer_id,status)`.

### `payments`

Mục đích: từng lần thử thanh toán invoice. Cột: `payment_code` UK, invoice/account FK, optional `transaction_id` FK+UK, amount > 0, fee >= 0, status CK, failure reason, times. Index account+time. Partial UK `invoice_id WHERE status='SUCCESS'` cho phép nhiều lần FAILED nhưng một lần thành công.

### `otp_codes`

Mục đích: challenge OTP đã hash. Cột: user FK, purpose CK, `code_hash`, optional transaction/payment FK, attempts (0..max, default max 5), expiry/consumed/created. CK expiry và chỉ tối đa một business target; index user+purpose+time. Backend sinh đúng 6 chữ số và expiry 5 phút.

### `refresh_tokens`

Mục đích: quản lý session refresh. Cột: user FK, `token_hash` UK, expiry/revoked/created; index user+expiry. Rotation tạo token mới và revoke token cũ.

### `password_reset_tokens`

Mục đích: reset password một lần. Cột: user FK, `token_hash` UK, expiry/used/created; index user+expiry. Thành công phải revoke refresh tokens.

### `notifications`

Mục đích: email/in-app event. Cột: user FK, type/status CK, event type, title/content, read/sent timestamps, `is_read`; index `(user_id,is_read,created_at)`. Nội dung không chứa OTP/token lâu dài.

### `audit_logs`

Mục đích: lịch sử hành vi, tách biệt financial transaction. Cột: nullable user FK (system event), action, resource type/id, before/after JSONB, IP INET, user-agent, correlation id, created_at. Index actor+time, resource, action+time. Append-only; layer redaction cấm password/hash/JWT/refresh/reset/OTP.

### `jobs`

Mục đích: trạng thái tác vụ nền. Cột: job type, status CK PENDING|PROCESSING|SUCCESS|FAILED, requester FK, parameters JSONB, result location, safe error, progress 0..100, lifecycle timestamps. Index status+time và requester+time.

## Financial Transaction Safety

Pseudo-flow bắt buộc cho internal transfer:

```sql
BEGIN;
SELECT * FROM accounts WHERE id IN (:source_id, :destination_id)
ORDER BY id FOR UPDATE;
-- recheck owner, status, currency, KYC and source balance
UPDATE accounts SET balance = ..., version = version + 1 WHERE id = ...;
INSERT INTO transaction_entries (...); -- DEBIT source, CREDIT destination
UPDATE transactions SET status = 'SUCCESS', completed_at = now() WHERE id = ...;
COMMIT;
```

`FOR UPDATE` ngăn hai request đồng thời cùng đọc một số dư cũ rồi cùng chi tiêu. Thứ tự ID cố định giảm deadlock. Recheck diễn ra sau lock vì validation trước OTP đã có thể lỗi thời. Balance, entries và trạng thái phải cùng một commit; chia nhiều commit có thể làm trừ tiền nhưng thiếu credit/ledger. Mọi exception trước commit phải `ROLLBACK`.

Account balance là cache giao dịch được bảo vệ/authoritative current state; ledger entries là lịch sử đối soát. Có thể chạy job kiểm tra `accounts.balance` bằng entry cuối. Không sửa entry lịch sử để “khớp”; dùng reversal transaction.

## Index strategy

Unique constraint đã tạo index riêng nên không tạo trùng trên username/email/account number/code. Composite index bắt đầu bằng cột ownership/status hay được filter rồi timestamp phục vụ danh sách phân trang. Không index các field ít chọn lọc đứng một mình như boolean `is_read`; ghép với user/time. JSONB chưa có GIN vì chưa có query ổn định—chỉ bổ sung khi có bằng chứng truy vấn.

## Soft delete và optimistic locking

Soft delete áp dụng users/customers/accounts/payees/invoices. Backend mặc định thêm `is_deleted=false`; restore chỉ khi unique/business rule còn thỏa. Financial transaction/entry/payment thành công không xóa. Với versioned record:

```sql
UPDATE accounts SET ..., version = version + 1
WHERE id = :id AND version = :expected_version;
```

Zero affected rows là conflict. Row lock vẫn bắt buộc cho balance; optimistic version phù hợp cập nhật thông tin thông thường.

## Migration và seed

Migration đầu tiên là `20260925_0001_initial_banking_schema`. Seed idempotent tạo roles, permissions, mappings, 4 users, 2 verified customers/accounts, payee, invoice, internal transaction + hai ledger entries và notification. Password được Argon2-hash trước khi insert; plaintext chỉ đến từ biến môi trường local và không được lưu DB.
