# Luồng nghiệp vụ

Các sơ đồ Mermaid là nguồn có thể render độc lập trong `docs/diagrams`.

## 1. Register + KYC

Sơ đồ: [register-kyc-flow.mmd](diagrams/register-kyc-flow.mmd). User/customer được tạo nguyên tử; password chỉ lưu hash. Hồ sơ KYC tách bảng để lưu lịch sử các lần nộp, còn `customers.kyc_status` là trạng thái hiện hành để kiểm tra nhanh.

## 2. Login

Sơ đồ: [login-flow.mmd](diagrams/login-flow.mmd). Login 2FA sử dụng `otp_codes.purpose=LOGIN_2FA`, không dùng chung ngữ cảnh với OTP giao dịch. Refresh token chỉ lưu hash và có thể revoke.

## 3. Internal Transfer + OTP

- Activity: [transfer-flow.mmd](diagrams/transfer-flow.mmd)
- Sequence: [transfer-sequence.mmd](diagrams/transfer-sequence.mmd)

Validation trước OTP chỉ là kiểm tra sơ bộ. Sau OTP, service bắt buộc mở DB transaction, khóa cả hai account theo thứ tự ID và kiểm tra lại số dư/trạng thái để tránh race condition. Commit duy nhất bao gồm balance, ledger và trạng thái transaction.

## 4. Interbank Transfer + OTP

- Activity: [interbank-flow.mmd](diagrams/interbank-flow.mmd)
- Sequence: [interbank-sequence.mmd](diagrams/interbank-sequence.mmd)

Đích ngoài được lưu snapshot vì không có FK nội bộ. Giao tiếp gateway phải có timeout/idempotency. Nếu timeout sau khi gửi, không tự kết luận FAILED và hoàn tiền mù; giữ PROCESSING để query/reconcile gateway.

## 5. Bill Payment + OTP

- Activity: [payment-flow.mmd](diagrams/payment-flow.mmd)
- Sequence: [payment-sequence.mmd](diagrams/payment-sequence.mmd)

Account và invoice cùng được khóa. Việc debit, tạo ledger, cập nhật invoice/payment/transaction nằm trong một transaction. Notification gửi sau commit để lỗi email không rollback tiền.

## 6. Employee Approve KYC

Sơ đồ: [kyc-flow.mmd](diagrams/kyc-flow.mmd). Employee không được duyệt request đã xử lý. Reject bắt buộc lý do. Customer và request được cập nhật cùng commit và audit chứa snapshot đã lọc PII theo chính sách log.

## 7. Forgot / Reset Password

Sơ đồ: [reset-password-flow.mmd](diagrams/reset-password-flow.mmd). Endpoint forgot về sau phải chống account enumeration. Reset token ngẫu nhiên chỉ lưu hash, có expiry và dùng một lần; reset thành công revoke mọi refresh token.

## 8. Generate Report Background Job

Sơ đồ: [background-job-flow.mmd](diagrams/background-job-flow.mmd). API tạo job rồi enqueue sau commit. Worker cập nhật progress/trạng thái, lưu đường dẫn artifact có thời hạn và tạo notification. Retry cần idempotent theo job id.

## Trạng thái quan trọng

- Transaction/Payment: `PENDING → OTP_REQUIRED → PROCESSING → SUCCESS|FAILED`; có thể `CANCELLED` trước xử lý.
- OTP: active khi chưa consumed, chưa expired và failed_attempts < max_attempts.
- KYC: `NOT_SUBMITTED → PENDING → VERIFIED|REJECTED`; reject có thể nộp lại.
- Job: `PENDING → PROCESSING → SUCCESS|FAILED`.

Không dùng xóa để biểu diễn thất bại. Audit event và notification được tạo theo kết quả cuối, nhưng audit bảo mật (ví dụ OTP sai) vẫn có thể ghi riêng.
