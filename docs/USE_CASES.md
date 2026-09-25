# Use Cases

Sơ đồ: [diagrams/use-case.mmd](diagrams/use-case.mmd).

## Ma trận actor — use case

| ID | Use case | Customer | Employee | Admin | Hệ thống ngoài |
|---|---|:---:|:---:|:---:|---|
| UC-01 | Register | ✓ | | | Email |
| UC-02 | Login / 2FA | ✓ | ✓ | ✓ | Email/SMS |
| UC-03 | Reset Password | ✓ | ✓ | ✓ | Email |
| UC-04 | Manage Profile | ✓ | giới hạn | | |
| UC-05 | Submit KYC | ✓ | | | |
| UC-06 | Approve/Reject KYC | | ✓ | ✓ | Email |
| UC-07 | View Account/Balance/History | sở hữu | theo quyền | tất cả | |
| UC-08 | Manage Payee | ✓ | | | |
| UC-09 | Internal Transfer + OTP | ✓ | | | Email/SMS |
| UC-10 | Interbank Transfer + OTP | ✓ | | | External Bank |
| UC-11 | View/Pay Invoice + OTP | ✓ | | | Email/SMS |
| UC-12 | Report/Statement/Export | cá nhân | phù hợp | hệ thống | Job Worker |
| UC-13 | View Notification | ✓ | ✓ | ✓ | |
| UC-14 | Manage Users/Employees | | | ✓ | |
| UC-15 | View Audit Log | | | ✓ | Job Worker |
| UC-16 | Import Customer/Invoice | | ✓ | ✓ | Job Worker |

## Đặc tả use case chính

### UC-01 Register

- **Mục tiêu:** tạo định danh đăng nhập và customer profile.
- **Tiền điều kiện:** chưa đăng nhập; dữ liệu định danh chưa tồn tại.
- **Luồng chính:** nhập dữ liệu → validate → hash password → tạo role CUSTOMER → tạo profile → audit → notification.
- **Luồng thay thế/ngoại lệ:** trùng dữ liệu hoặc password yếu; transaction DB rollback nếu một bước lỗi.
- **Hậu điều kiện:** customer tồn tại với KYC `NOT_SUBMITTED`.

### UC-02 Login / 2FA

- **Mục tiêu:** nhận access/refresh token.
- **Tiền điều kiện:** user ACTIVE, chưa soft-delete.
- **Luồng chính:** verify credentials → nếu bật 2FA tạo/verify OTP `LOGIN_2FA` → phát hành token → audit.
- **Ngoại lệ:** thông tin sai, OTP sai/hết hạn/đủ 5 lần; phản hồi không tiết lộ username có tồn tại.

### UC-05/06 Submit và Review KYC

- Customer nộp metadata tài liệu, tạo `kyc_requests.PENDING` và customer chuyển `PENDING`.
- Employee có `kyc:approve` khóa/đọc request hiện tại, approve hoặc reject kèm lý do.
- Hệ thống cập nhật request/customer cùng transaction, tăng version, audit trước/sau và gửi notification.

### UC-07 View Account/Balance/History

- Customer chỉ xem account thuộc profile mình; Employee/Admin theo permission.
- History lấy từ `transaction_entries`, filter khoảng thời gian/type/status, sort allow-list và pagination.
- Dòng statement hiển thị debit/credit cùng `balance_after`; opening balance lấy snapshot gần nhất trước kỳ hoặc suy ra từ dòng đầu.

### UC-09 Internal Transfer

- **Tiền điều kiện:** KYC VERIFIED; source thuộc customer, ACTIVE, cùng currency, đủ balance.
- **Luồng chính:** tạo transaction OTP_REQUIRED → verify OTP → DB transaction khóa hai account theo ID → recheck → debit/credit → hai ledger entries → SUCCESS → audit/notify.
- **Ngoại lệ:** idempotency trùng trả kết quả cũ; thiếu tiền/OTP lỗi thành FAILED/CANCELLED phù hợp; lỗi DB rollback.

### UC-10 Interbank Transfer

- Lưu snapshot `destination_account_number/bank_code/account_name`; `destination_account_id` để null.
- Gọi mock gateway qua adapter với idempotency key. Kết quả chắc chắn rejected → FAILED; accepted → debit/ledger/SUCCESS; timeout không rõ kết quả → PROCESSING để đối soát.

### UC-11 Pay Invoice

- Invoice phải thuộc customer, UNPAID và số tiền khớp.
- Có thể tồn tại nhiều payment attempt FAILED, nhưng partial unique index chỉ cho một SUCCESS.
- Khi OTP hợp lệ: khóa account và invoice → debit → ledger → invoice PAID → payment/transaction SUCCESS trong một commit.

### UC-12 Report/Statement/Export

- Báo cáo nhỏ query trực tiếp transaction/ledger. Export lớn tạo `jobs.PENDING`; worker tạo CSV/Excel/PDF, cập nhật result location và notification.
- Permission và ownership được giữ trong tham số job đã chuẩn hóa; worker phải kiểm tra lại quyền tại thời điểm chạy.

### UC-14 Manage Users

- Admin tìm kiếm/filter/page, khóa/mở khóa, soft-delete/restore và quản lý employee.
- Không cho employee thay đổi role ADMIN; không hard-delete record có liên hệ tài chính; mọi thay đổi có audit.

### UC-15 View Audit Log

- Chỉ ADMIN với `audit_logs:read`; filter theo actor/action/resource/time và export bằng job.
- Audit là append-only ở tầng ứng dụng; snapshot đã redact bí mật.

## Quy tắc chung

Mọi use case đọc danh sách hỗ trợ search/filter/sort/page theo allow-list. Mọi mutation nhạy cảm kiểm tra authentication, permission, ownership, soft-delete, version và ghi audit. Transaction tài chính không cung cấp use case DELETE.
