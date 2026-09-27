# Từ điển dữ liệu — Banking Management System

Tài liệu này mô tả schema PostgreSQL tại migration `20260925_0001`. `Không` ở cột Null nghĩa là trường bắt buộc. Tất cả thời gian dùng `TIMESTAMPTZ`; dữ liệu tiền dùng `NUMERIC(19,4)` và phải ánh xạ sang `Decimal` trong Python.

## Tổng quan

| Nhóm | Bảng |
|---|---|
| Phân quyền | `roles`, `permissions`, `role_permissions`, `users` |
| Khách hàng/KYC | `customers`, `kyc_requests` |
| Ngân hàng | `accounts`, `payees`, `transactions`, `transaction_entries` |
| Hóa đơn | `invoices`, `payments` |
| Xác thực | `otp_codes`, `refresh_tokens`, `password_reset_tokens` |
| Vận hành | `notifications`, `audit_logs`, `jobs` |

## 1. `roles`

Lưu ba vai trò nghiệp vụ của hệ thống.

| Trường | Kiểu | Null | Ràng buộc / mặc định | Ý nghĩa |
|---|---|:---:|---|---|
| `id` | `SMALLINT` | Không | PK, tự tăng | Định danh role. |
| `name` | `VARCHAR(30)` | Không | UNIQUE; ADMIN, EMPLOYEE hoặc CUSTOMER | Tên role ổn định dùng trong RBAC. |
| `description` | `VARCHAR(255)` | Có | — | Mô tả role. |
| `created_at` | `TIMESTAMPTZ` | Không | `now()` | Thời điểm tạo. |

Quan hệ: một role có nhiều users và nhiều permissions qua `role_permissions`.

## 2. `permissions`

Danh mục quyền theo cấu trúc `resource:action`.

| Trường | Kiểu | Null | Ràng buộc / mặc định | Ý nghĩa |
|---|---|:---:|---|---|
| `id` | `INTEGER` | Không | PK, tự tăng | Định danh permission. |
| `code` | `VARCHAR(100)` | Không | UNIQUE | Mã hoàn chỉnh, ví dụ `transfers:create`. |
| `resource` | `VARCHAR(50)` | Không | UNIQUE cùng `action` | Tài nguyên được bảo vệ. |
| `action` | `VARCHAR(30)` | Không | UNIQUE cùng `resource` | Hành động như read, update, create. |
| `description` | `VARCHAR(255)` | Có | — | Giải thích quyền. |

## 3. `role_permissions`

Bảng nối many-to-many giữa role và permission.

| Trường | Kiểu | Null | Ràng buộc / mặc định | Ý nghĩa |
|---|---|:---:|---|---|
| `role_id` | `SMALLINT` | Không | PK, FK → `roles.id`, CASCADE | Role được cấp quyền. |
| `permission_id` | `INTEGER` | Không | PK, FK → `permissions.id`, CASCADE | Permission được gán. |

Khóa chính ghép `(role_id, permission_id)` ngăn gán trùng.

## 4. `users`

Định danh đăng nhập cho Admin, Employee và Customer.

| Trường | Kiểu | Null | Ràng buộc / mặc định | Ý nghĩa |
|---|---|:---:|---|---|
| `id` | `BIGINT` | Không | PK, tự tăng | Định danh user. |
| `role_id` | `SMALLINT` | Không | FK → `roles.id`, RESTRICT | Role hiện tại của user. |
| `username` | `VARCHAR(50)` | Không | UNIQUE | Tên đăng nhập. |
| `email` | `VARCHAR(255)` | Không | UNIQUE | Email đăng nhập/nhận thông báo. |
| `password_hash` | `VARCHAR(255)` | Không | — | Password đã hash; không lưu plaintext. |
| `status` | `VARCHAR(20)` | Không | `PENDING`; CHECK | PENDING, ACTIVE, LOCKED hoặc DISABLED. |
| `two_factor_enabled` | `BOOLEAN` | Không | `false` | Có yêu cầu OTP khi login hay không. |
| `last_login_at` | `TIMESTAMPTZ` | Có | — | Lần đăng nhập thành công gần nhất. |
| `is_deleted` | `BOOLEAN` | Không | `false` | Cờ soft-delete. |
| `deleted_at` | `TIMESTAMPTZ` | Có | — | Thời điểm soft-delete. |
| `deleted_by` | `BIGINT` | Có | FK → `users.id`, RESTRICT | User thực hiện soft-delete. |
| `created_at` | `TIMESTAMPTZ` | Không | `now()` | Thời điểm tạo. |
| `updated_at` | `TIMESTAMPTZ` | Không | `now()` | Thời điểm cập nhật gần nhất. |

Index đáng chú ý: partial index `username WHERE is_deleted=false`. Một user CUSTOMER có tối đa một customer profile.

## 5. `customers`

Hồ sơ nghiệp vụ của khách hàng.

| Trường | Kiểu | Null | Ràng buộc / mặc định | Ý nghĩa |
|---|---|:---:|---|---|
| `id` | `BIGINT` | Không | PK, tự tăng | Định danh customer. |
| `user_id` | `BIGINT` | Không | UNIQUE, FK → `users.id`, RESTRICT | User đăng nhập tương ứng. |
| `customer_code` | `VARCHAR(30)` | Không | UNIQUE | Mã khách hàng nghiệp vụ. |
| `full_name` | `VARCHAR(150)` | Không | — | Họ tên pháp lý. |
| `date_of_birth` | `DATE` | Không | — | Ngày sinh. |
| `identity_number` | `VARCHAR(30)` | Không | UNIQUE | CCCD/hộ chiếu hoặc định danh tương đương. |
| `phone` | `VARCHAR(20)` | Không | UNIQUE | Số điện thoại. |
| `address` | `TEXT` | Có | — | Địa chỉ liên hệ. |
| `kyc_status` | `VARCHAR(20)` | Không | `NOT_SUBMITTED`; CHECK | NOT_SUBMITTED, PENDING, VERIFIED hoặc REJECTED. |
| `kyc_verified_at` | `TIMESTAMPTZ` | Có | — | Thời điểm được xác minh. |
| `version` | `INTEGER` | Không | `1`; CHECK > 0 | Optimistic locking. |
| `is_deleted` | `BOOLEAN` | Không | `false` | Cờ soft-delete. |
| `deleted_at` | `TIMESTAMPTZ` | Có | — | Thời điểm soft-delete. |
| `deleted_by` | `BIGINT` | Có | FK → `users.id`, RESTRICT | Người thực hiện xóa mềm. |
| `created_at` | `TIMESTAMPTZ` | Không | `now()` | Thời điểm tạo. |
| `updated_at` | `TIMESTAMPTZ` | Không | `now()` | Thời điểm cập nhật. |

Index: `kyc_status`. Một customer có nhiều account, payee, invoice và KYC request.

## 6. `kyc_requests`

Lưu lịch sử các lần nộp và xét duyệt KYC.

| Trường | Kiểu | Null | Ràng buộc / mặc định | Ý nghĩa |
|---|---|:---:|---|---|
| `id` | `BIGINT` | Không | PK, tự tăng | Định danh yêu cầu KYC. |
| `customer_id` | `BIGINT` | Không | FK → `customers.id`, RESTRICT | Khách hàng nộp hồ sơ. |
| `status` | `VARCHAR(20)` | Không | `PENDING`; CHECK | PENDING, APPROVED hoặc REJECTED. |
| `document_data` | `JSONB` | Không | `{}` | Metadata/path tài liệu, không chứa binary. |
| `submitted_at` | `TIMESTAMPTZ` | Không | `now()` | Thời điểm nộp. |
| `reviewed_by` | `BIGINT` | Có | FK → `users.id`, RESTRICT | Employee/Admin xét duyệt. |
| `reviewed_at` | `TIMESTAMPTZ` | Có | — | Thời điểm xét duyệt. |
| `rejection_reason` | `TEXT` | Có | — | Lý do từ chối. |

Index: `(customer_id, status)`.

## 7. `accounts`

Tài khoản ngân hàng và số dư hiện tại.

| Trường | Kiểu | Null | Ràng buộc / mặc định | Ý nghĩa |
|---|---|:---:|---|---|
| `id` | `BIGINT` | Không | PK, tự tăng | Định danh nội bộ. |
| `customer_id` | `BIGINT` | Không | FK → `customers.id`, RESTRICT | Chủ tài khoản. |
| `account_number` | `VARCHAR(34)` | Không | UNIQUE | Số tài khoản/IBAN. |
| `account_type` | `VARCHAR(20)` | Không | `CHECKING`; CHECK | CHECKING hoặc SAVINGS. |
| `status` | `VARCHAR(20)` | Không | `ACTIVE`; CHECK | ACTIVE, LOCKED hoặc CLOSED. |
| `currency` | `VARCHAR(3)` | Không | `VND`; dài 3 ký tự | Mã tiền tệ ISO. |
| `balance` | `NUMERIC(19,4)` | Không | `0`; CHECK >= 0 | Số dư hiện tại. |
| `version` | `INTEGER` | Không | `1`; CHECK > 0 | Optimistic locking. |
| `is_deleted` | `BOOLEAN` | Không | `false` | Cờ soft-delete. |
| `deleted_at` | `TIMESTAMPTZ` | Có | — | Thời điểm xóa mềm. |
| `deleted_by` | `BIGINT` | Có | FK → `users.id`, RESTRICT | Người thực hiện xóa mềm. |
| `created_at` | `TIMESTAMPTZ` | Không | `now()` | Thời điểm tạo. |
| `updated_at` | `TIMESTAMPTZ` | Không | `now()` | Thời điểm cập nhật. |

Index: `(customer_id, status)`. Balance chỉ được đổi trong cùng DB transaction với ledger entry.

## 8. `payees`

Danh sách người thụ hưởng do khách hàng lưu.

| Trường | Kiểu | Null | Ràng buộc / mặc định | Ý nghĩa |
|---|---|:---:|---|---|
| `id` | `BIGINT` | Không | PK, tự tăng | Định danh payee. |
| `customer_id` | `BIGINT` | Không | FK → `customers.id`, RESTRICT | Chủ danh sách thụ hưởng. |
| `nickname` | `VARCHAR(100)` | Không | — | Tên gợi nhớ. |
| `account_number` | `VARCHAR(34)` | Không | UNIQUE theo customer+bank | Số tài khoản nhận. |
| `account_name` | `VARCHAR(150)` | Không | — | Tên chủ tài khoản tại thời điểm lưu. |
| `bank_code` | `VARCHAR(20)` | Không | UNIQUE theo customer+account | Mã ngân hàng. |
| `is_internal` | `BOOLEAN` | Không | `false` | Có thuộc ngân hàng nội bộ không. |
| `linked_account_id` | `BIGINT` | Có | FK → `accounts.id`, RESTRICT | Account nội bộ tương ứng; bắt buộc nếu internal. |
| `is_deleted` | `BOOLEAN` | Không | `false` | Cờ soft-delete. |
| `deleted_at` | `TIMESTAMPTZ` | Có | — | Thời điểm xóa mềm. |
| `deleted_by` | `BIGINT` | Có | FK → `users.id`, RESTRICT | Người thực hiện xóa mềm. |
| `created_at` | `TIMESTAMPTZ` | Không | `now()` | Thời điểm tạo. |
| `updated_at` | `TIMESTAMPTZ` | Không | `now()` | Thời điểm cập nhật. |

Unique ghép: `(customer_id, bank_code, account_number)`.

## 9. `transactions`

Lưu lệnh giao dịch và vòng đời nghiệp vụ; không dùng thay audit log.

| Trường | Kiểu | Null | Ràng buộc / mặc định | Ý nghĩa |
|---|---|:---:|---|---|
| `id` | `BIGINT` | Không | PK, tự tăng | Định danh transaction. |
| `transaction_code` | `VARCHAR(40)` | Không | UNIQUE | Mã giao dịch công khai. |
| `transaction_type` | `VARCHAR(30)` | Không | CHECK | DEPOSIT, WITHDRAWAL, INTERNAL_TRANSFER, INTERBANK_TRANSFER, BILL_PAYMENT, FEE hoặc REVERSAL. |
| `status` | `VARCHAR(20)` | Không | `PENDING`; CHECK | PENDING, OTP_REQUIRED, PROCESSING, SUCCESS, FAILED hoặc CANCELLED. |
| `source_account_id` | `BIGINT` | Có | FK → `accounts.id`, RESTRICT | Tài khoản nguồn nếu có. |
| `destination_account_id` | `BIGINT` | Có | FK → `accounts.id`, RESTRICT | Tài khoản đích nội bộ; null với đích ngoài. |
| `destination_account_number` | `VARCHAR(34)` | Có | — | Snapshot số tài khoản đích ngoài. |
| `destination_bank_code` | `VARCHAR(20)` | Có | — | Snapshot mã ngân hàng đích ngoài. |
| `destination_account_name` | `VARCHAR(150)` | Có | — | Snapshot tên người nhận ngoài. |
| `amount` | `NUMERIC(19,4)` | Không | CHECK > 0 | Số tiền giao dịch, chưa gồm phí. |
| `fee` | `NUMERIC(19,4)` | Không | `0`; CHECK >= 0 | Phí giao dịch. |
| `currency` | `VARCHAR(3)` | Không | `VND`; dài 3 ký tự | Loại tiền. |
| `description` | `VARCHAR(500)` | Có | — | Nội dung giao dịch. |
| `idempotency_key` | `VARCHAR(100)` | Có | UNIQUE | Chống xử lý lặp cùng yêu cầu. |
| `failure_code` | `VARCHAR(50)` | Có | — | Mã lỗi ổn định. |
| `failure_reason` | `VARCHAR(500)` | Có | — | Lý do thất bại an toàn. |
| `initiated_by` | `BIGINT` | Có | FK → `users.id`, RESTRICT | User khởi tạo hoặc null nếu hệ thống. |
| `created_at` | `TIMESTAMPTZ` | Không | `now()` | Thời điểm tạo lệnh. |
| `completed_at` | `TIMESTAMPTZ` | Có | — | Thời điểm kết thúc. |

CHECK ngăn source và destination cùng một account. Index: `(source_account_id, created_at)`, `(destination_account_id, created_at)`, `(status, created_at)`.

## 10. `transaction_entries`

Sổ cái theo từng tài khoản, là nguồn tạo lịch sử và sao kê.

| Trường | Kiểu | Null | Ràng buộc / mặc định | Ý nghĩa |
|---|---|:---:|---|---|
| `id` | `BIGINT` | Không | PK, tự tăng | Định danh ledger entry. |
| `transaction_id` | `BIGINT` | Không | FK → `transactions.id`, RESTRICT | Giao dịch sinh ra entry. |
| `account_id` | `BIGINT` | Không | FK → `accounts.id`, RESTRICT | Account bị tác động. |
| `entry_type` | `VARCHAR(10)` | Không | DEBIT hoặc CREDIT | Chiều biến động. |
| `amount` | `NUMERIC(19,4)` | Không | CHECK > 0 | Số tiền biến động. |
| `balance_before` | `NUMERIC(19,4)` | Không | CHECK >= 0 | Số dư ngay trước khi post. |
| `balance_after` | `NUMERIC(19,4)` | Không | CHECK >= 0 và đúng phép tính | Số dư ngay sau khi post. |
| `created_at` | `TIMESTAMPTZ` | Không | `now()` | Thời điểm post ledger. |

Unique `(transaction_id, account_id, entry_type)`. CHECK yêu cầu DEBIT: `after=before-amount`; CREDIT: `after=before+amount`. Index `(account_id, created_at)`.

## 11. `invoices`

Hóa đơn điện, nước, internet hoặc điện thoại của khách hàng.

| Trường | Kiểu | Null | Ràng buộc / mặc định | Ý nghĩa |
|---|---|:---:|---|---|
| `id` | `BIGINT` | Không | PK, tự tăng | Định danh invoice. |
| `customer_id` | `BIGINT` | Không | FK → `customers.id`, RESTRICT | Khách hàng phải thanh toán. |
| `invoice_code` | `VARCHAR(50)` | Không | UNIQUE | Mã hóa đơn. |
| `provider_code` | `VARCHAR(30)` | Không | — | Mã nhà cung cấp dịch vụ. |
| `service_type` | `VARCHAR(20)` | Không | CHECK | ELECTRICITY, WATER, INTERNET hoặc PHONE. |
| `customer_reference` | `VARCHAR(50)` | Không | — | Mã thuê bao/hợp đồng tại nhà cung cấp. |
| `billing_period` | `VARCHAR(20)` | Có | — | Kỳ hóa đơn, ví dụ `2026-09`. |
| `amount` | `NUMERIC(19,4)` | Không | CHECK > 0 | Số tiền hóa đơn. |
| `currency` | `VARCHAR(3)` | Không | `VND`; dài 3 ký tự | Loại tiền. |
| `due_date` | `DATE` | Không | — | Hạn thanh toán. |
| `status` | `VARCHAR(20)` | Không | `UNPAID`; CHECK | UNPAID, PENDING, PAID, OVERDUE hoặc CANCELLED. |
| `paid_at` | `TIMESTAMPTZ` | Có | — | Thời điểm thanh toán thành công. |
| `version` | `INTEGER` | Không | `1`; CHECK > 0 | Optimistic locking. |
| `is_deleted` | `BOOLEAN` | Không | `false` | Cờ soft-delete. |
| `deleted_at` | `TIMESTAMPTZ` | Có | — | Thời điểm xóa mềm. |
| `deleted_by` | `BIGINT` | Có | FK → `users.id`, RESTRICT | Người thực hiện xóa mềm. |
| `created_at` | `TIMESTAMPTZ` | Không | `now()` | Thời điểm tạo. |
| `updated_at` | `TIMESTAMPTZ` | Không | `now()` | Thời điểm cập nhật. |

Index `(customer_id, status)`. Một invoice có thể có nhiều payment attempt nhưng tối đa một payment SUCCESS.

## 12. `payments`

Lưu từng lần thử thanh toán hóa đơn.

| Trường | Kiểu | Null | Ràng buộc / mặc định | Ý nghĩa |
|---|---|:---:|---|---|
| `id` | `BIGINT` | Không | PK, tự tăng | Định danh payment. |
| `payment_code` | `VARCHAR(40)` | Không | UNIQUE | Mã thanh toán công khai. |
| `invoice_id` | `BIGINT` | Không | FK → `invoices.id`, RESTRICT | Hóa đơn cần thanh toán. |
| `account_id` | `BIGINT` | Không | FK → `accounts.id`, RESTRICT | Account trả tiền. |
| `transaction_id` | `BIGINT` | Có | UNIQUE, FK → `transactions.id`, RESTRICT | Financial transaction tương ứng khi được post. |
| `amount` | `NUMERIC(19,4)` | Không | CHECK > 0 | Số tiền thanh toán. |
| `fee` | `NUMERIC(19,4)` | Không | `0`; CHECK >= 0 | Phí thanh toán. |
| `status` | `VARCHAR(20)` | Không | `PENDING`; CHECK | PENDING, OTP_REQUIRED, PROCESSING, SUCCESS, FAILED hoặc CANCELLED. |
| `failure_reason` | `VARCHAR(500)` | Có | — | Lý do thất bại. |
| `created_at` | `TIMESTAMPTZ` | Không | `now()` | Thời điểm tạo lần thử. |
| `completed_at` | `TIMESTAMPTZ` | Có | — | Thời điểm hoàn tất. |

Index `(account_id, created_at)`. Partial unique index trên `invoice_id WHERE status='SUCCESS'` bảo đảm không trả thành công hai lần.

## 13. `otp_codes`

Challenge OTP cho login 2FA và giao dịch. Chỉ lưu hash, không lưu mã OTP plaintext.

| Trường | Kiểu | Null | Ràng buộc / mặc định | Ý nghĩa |
|---|---|:---:|---|---|
| `id` | `BIGINT` | Không | PK, tự tăng | Định danh OTP challenge. |
| `user_id` | `BIGINT` | Không | FK → `users.id`, RESTRICT | User nhận/xác minh OTP. |
| `purpose` | `VARCHAR(30)` | Không | CHECK | LOGIN_2FA, TRANSFER, BILL_PAYMENT hoặc PASSWORD_RESET. |
| `code_hash` | `VARCHAR(255)` | Không | — | Hash của OTP 6 chữ số. |
| `transaction_id` | `BIGINT` | Có | FK → `transactions.id`, RESTRICT | Transfer được xác thực. |
| `payment_id` | `BIGINT` | Có | FK → `payments.id`, RESTRICT | Payment được xác thực. |
| `failed_attempts` | `SMALLINT` | Không | `0`; từ 0 đến max | Số lần nhập sai. |
| `max_attempts` | `SMALLINT` | Không | `5`; CHECK > 0 | Giới hạn lần thử. |
| `expires_at` | `TIMESTAMPTZ` | Không | Phải sau `created_at` | Hạn dùng, nghiệp vụ đặt 5 phút. |
| `consumed_at` | `TIMESTAMPTZ` | Có | — | Thời điểm OTP được dùng thành công. |
| `created_at` | `TIMESTAMPTZ` | Không | `now()` | Thời điểm phát sinh. |

Chỉ tối đa một trong `transaction_id`, `payment_id` được có giá trị. Index `(user_id, purpose, created_at)`.

## 14. `refresh_tokens`

Quản lý refresh-token session; database chỉ lưu hash.

| Trường | Kiểu | Null | Ràng buộc / mặc định | Ý nghĩa |
|---|---|:---:|---|---|
| `id` | `BIGINT` | Không | PK, tự tăng | Định danh token record. |
| `user_id` | `BIGINT` | Không | FK → `users.id`, RESTRICT | Chủ token. |
| `token_hash` | `VARCHAR(255)` | Không | UNIQUE | Hash refresh token. |
| `expires_at` | `TIMESTAMPTZ` | Không | — | Hạn sử dụng. |
| `revoked_at` | `TIMESTAMPTZ` | Có | — | Thời điểm thu hồi; null nếu còn hiệu lực. |
| `created_at` | `TIMESTAMPTZ` | Không | `now()` | Thời điểm phát hành. |

Index `(user_id, expires_at)`.

## 15. `password_reset_tokens`

Token dùng một lần để đặt lại mật khẩu; database chỉ lưu hash.

| Trường | Kiểu | Null | Ràng buộc / mặc định | Ý nghĩa |
|---|---|:---:|---|---|
| `id` | `BIGINT` | Không | PK, tự tăng | Định danh token record. |
| `user_id` | `BIGINT` | Không | FK → `users.id`, RESTRICT | User yêu cầu reset. |
| `token_hash` | `VARCHAR(255)` | Không | UNIQUE | Hash reset token. |
| `expires_at` | `TIMESTAMPTZ` | Không | — | Hạn sử dụng. |
| `used_at` | `TIMESTAMPTZ` | Có | — | Thời điểm đã dùng; null nếu chưa dùng. |
| `created_at` | `TIMESTAMPTZ` | Không | `now()` | Thời điểm tạo. |

Index `(user_id, expires_at)`. Reset thành công phải revoke các refresh token đang hoạt động.

## 16. `notifications`

Thông báo EMAIL hoặc IN_APP gửi tới user.

| Trường | Kiểu | Null | Ràng buộc / mặc định | Ý nghĩa |
|---|---|:---:|---|---|
| `id` | `BIGINT` | Không | PK, tự tăng | Định danh notification. |
| `user_id` | `BIGINT` | Không | FK → `users.id`, RESTRICT | Người nhận. |
| `notification_type` | `VARCHAR(20)` | Không | EMAIL hoặc IN_APP | Kênh thông báo. |
| `event_type` | `VARCHAR(50)` | Không | — | Loại sự kiện như KYC_APPROVED, TRANSFER_SUCCESS. |
| `title` | `VARCHAR(200)` | Không | — | Tiêu đề. |
| `content` | `TEXT` | Không | — | Nội dung đã render; không lưu OTP/token lâu dài. |
| `status` | `VARCHAR(20)` | Không | `PENDING`; CHECK | PENDING, SENT, FAILED hoặc READ. |
| `is_read` | `BOOLEAN` | Không | `false` | Trạng thái đọc của in-app notification. |
| `read_at` | `TIMESTAMPTZ` | Có | — | Thời điểm đọc. |
| `sent_at` | `TIMESTAMPTZ` | Có | — | Thời điểm gửi thành công. |
| `created_at` | `TIMESTAMPTZ` | Không | `now()` | Thời điểm tạo. |

Index `(user_id, is_read, created_at)`.

## 17. `audit_logs`

Lịch sử hành vi user/hệ thống, tách biệt với lịch sử tài chính.

| Trường | Kiểu | Null | Ràng buộc / mặc định | Ý nghĩa |
|---|---|:---:|---|---|
| `id` | `BIGINT` | Không | PK, tự tăng | Định danh audit event. |
| `user_id` | `BIGINT` | Có | FK → `users.id`, RESTRICT | Actor; null với system event. |
| `action` | `VARCHAR(60)` | Không | — | Hành động như LOGIN_SUCCESS, KYC_APPROVED. |
| `resource_type` | `VARCHAR(60)` | Không | — | Loại resource bị tác động. |
| `resource_id` | `VARCHAR(100)` | Có | — | ID resource ở dạng text. |
| `before_data` | `JSONB` | Có | — | Snapshot trước thay đổi đã redact. |
| `after_data` | `JSONB` | Có | — | Snapshot sau thay đổi đã redact. |
| `ip_address` | `INET` | Có | — | IP nguồn. |
| `user_agent` | `VARCHAR(500)` | Có | — | User-Agent của client. |
| `correlation_id` | `VARCHAR(100)` | Có | — | ID liên kết request/job/log. |
| `created_at` | `TIMESTAMPTZ` | Không | `now()` | Thời điểm xảy ra. |

Index: `(user_id, created_at)`, `(resource_type, resource_id)`, `(action, created_at)`. Tuyệt đối không ghi password, hash, JWT, refresh/reset token hoặc OTP vào JSONB.

## 18. `jobs`

Theo dõi tác vụ nền như gửi email hoặc sinh CSV/Excel/PDF.

| Trường | Kiểu | Null | Ràng buộc / mặc định | Ý nghĩa |
|---|---|:---:|---|---|
| `id` | `BIGINT` | Không | PK, tự tăng | Định danh job. |
| `job_type` | `VARCHAR(50)` | Không | — | Loại công việc, ví dụ EXPORT_STATEMENT. |
| `status` | `VARCHAR(20)` | Không | `PENDING`; CHECK | PENDING, PROCESSING, SUCCESS hoặc FAILED. |
| `requested_by` | `BIGINT` | Có | FK → `users.id`, RESTRICT | User yêu cầu; null với system job. |
| `parameters` | `JSONB` | Không | `{}` | Tham số đã chuẩn hóa, không chứa secret. |
| `result_location` | `VARCHAR(500)` | Có | — | Vị trí file kết quả hoặc object key. |
| `error_message` | `TEXT` | Có | — | Lỗi an toàn để hiển thị/điều tra. |
| `progress` | `SMALLINT` | Không | `0`; CHECK 0..100 | Phần trăm tiến độ. |
| `created_at` | `TIMESTAMPTZ` | Không | `now()` | Thời điểm tạo job. |
| `started_at` | `TIMESTAMPTZ` | Có | — | Thời điểm worker bắt đầu. |
| `completed_at` | `TIMESTAMPTZ` | Có | — | Thời điểm kết thúc. |

Index: `(status, created_at)` và `(requested_by, created_at)`.

## Quan hệ chính

```text
roles 1 ── N users
roles N ── N permissions
users 1 ── 0..1 customers
customers 1 ── N accounts / payees / invoices / kyc_requests
transactions 1 ── N transaction_entries
accounts 1 ── N transaction_entries
invoices 1 ── N payments
payments 0..1 ── 1 transactions
users 1 ── N otp_codes / tokens / notifications / audit_logs / jobs
```

## Quy tắc dữ liệu quan trọng

- Không hard-delete transaction, ledger entry hoặc payment hoàn tất.
- `transactions` mô tả nghiệp vụ; `audit_logs` mô tả hành vi; hai bảng không thay thế nhau.
- Internal transfer có hai ledger entry: DEBIT nguồn và CREDIT đích.
- Interbank transfer để `destination_account_id` null và giữ snapshot đích ngoài.
- `accounts.balance`, ledger entries và trạng thái transaction phải được cập nhật trong một DB transaction.
- Soft-delete áp dụng cho users, customers, accounts, payees và invoices.
- Optimistic versioning áp dụng cho customers, accounts và invoices.
