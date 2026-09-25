# Đặc tả yêu cầu phần mềm (SRS) — Banking Management System

## 1. Giới thiệu

Tài liệu mô tả yêu cầu giai đoạn thiết kế cho hệ thống quản lý ngân hàng trực tuyến. Backend mục tiêu là FastAPI nhưng giai đoạn này chỉ gồm phân tích, kiến trúc và cơ sở dữ liệu.

## 2. Mục tiêu hệ thống

Hệ thống quản lý khách hàng, KYC, tài khoản, giao dịch, người thụ hưởng, hóa đơn, báo cáo và thông báo; hỗ trợ chuyển khoản an toàn, truy vết đầy đủ và phân quyền rõ ràng.

## 3. Phạm vi

Trong phạm vi: đăng ký/xác thực ở mức thiết kế; RBAC; quản lý dữ liệu; chuyển khoản nội bộ/liên ngân hàng mock; thanh toán hóa đơn; OTP; báo cáo/sao kê; import/export; audit; job nền. Ngoài phạm vi hiện tại: router/API, JWT runtime, service nghiệp vụ, Celery, sinh file và frontend.

## 4. Các bên liên quan

Khách hàng, nhân viên vận hành/KYC, quản trị viên, giảng viên/nhóm phát triển, đơn vị cung cấp hóa đơn, ngân hàng ngoài, nhà cung cấp email/SMS.

## 5. Actor

- `CUSTOMER`: thao tác trên dữ liệu thuộc chính mình; chỉ giao dịch khi KYC `VERIFIED`.
- `EMPLOYEE`: tra cứu khách hàng/tài khoản/giao dịch, cập nhật trường được phép, duyệt KYC.
- `ADMIN`: quản lý user/employee, xem toàn hệ thống, audit và báo cáo, khôi phục bản ghi phù hợp.
- External Bank, Email/SMS Service và Job Worker là actor hệ thống.

## 6. Yêu cầu chức năng

### FR-001 — Đăng ký khách hàng

- **Actor:** Customer. **Mô tả:** tạo user role CUSTOMER và customer profile.
- **Input:** username, email, password, thông tin cá nhân. **Output:** hồ sơ mới và thông báo đăng ký.
- **Pre-condition:** username/email/định danh chưa tồn tại. **Post-condition:** user `PENDING` hoặc `ACTIVE`, KYC `NOT_SUBMITTED`.
- **Main Flow:** validate → hash password → tạo user/customer trong một transaction → audit/notification.
- **Alternative Flow:** dữ liệu trùng được trả lỗi theo trường. **Exception:** lỗi DB rollback toàn bộ.

### FR-002 — Đăng nhập

- **Actor:** mọi user. **Mô tả:** xác thực thông tin và phát hành access/refresh token; hỗ trợ 2FA.
- **Input:** username/password, OTP nếu bật 2FA. **Output:** token hoặc challenge.
- **Pre-condition:** user tồn tại, chưa xóa/khóa. **Post-condition:** lưu hash refresh token và `last_login_at`.
- **Main Flow:** verify password → tùy chọn OTP `LOGIN_2FA` → phát hành token → audit.
- **Alternative Flow:** 2FA tạo challenge 5 phút. **Exception:** phản hồi lỗi chung và audit `LOGIN_FAILED`.

### FR-003 — Quên/đặt lại mật khẩu

- **Actor:** user. **Mô tả:** đặt lại mật khẩu bằng token một lần.
- **Input:** email; token và password mới. **Output:** phản hồi trung tính/trạng thái thành công.
- **Pre-condition:** user hợp lệ. **Post-condition:** password hash đổi, token đã dùng, refresh token bị revoke.
- **Main Flow:** sinh token ngẫu nhiên → lưu hash/expiry → gửi link → xác minh → đổi mật khẩu.
- **Alternative Flow:** email không tồn tại vẫn trả cùng phản hồi. **Exception:** token hết hạn/đã dùng bị từ chối.

### FR-004 — Quản lý hồ sơ và KYC

- **Actor:** Customer. **Mô tả:** xem/cập nhật trường cho phép và nộp KYC.
- **Input:** profile, metadata tài liệu. **Output:** KYC request `PENDING`.
- **Pre-condition:** user sở hữu customer. **Post-condition:** version tăng, audit được ghi.
- **Main Flow:** validate → cập nhật profile/nộp hồ sơ → audit.
- **Alternative Flow:** nộp lại sau khi bị từ chối. **Exception:** xung đột version trả conflict.

### FR-005 — Duyệt/từ chối KYC

- **Actor:** Employee. **Mô tả:** xét hồ sơ đang chờ.
- **Input:** request id, quyết định, lý do nếu từ chối. **Output:** trạng thái KYC.
- **Pre-condition:** permission `kyc:approve`, request `PENDING`. **Post-condition:** request và customer cập nhật nhất quán.
- **Main Flow:** kiểm tra → approve/reject → tăng version → audit → notification.
- **Alternative Flow:** yêu cầu nộp lại bằng quyết định reject có lý do. **Exception:** request đã xử lý trả conflict.

### FR-006 — Xem tài khoản và số dư

- **Actor:** Customer/Employee/Admin. **Mô tả:** tra cứu theo phạm vi quyền.
- **Input:** account id, filter/pagination. **Output:** tài khoản và số dư hiện tại.
- **Pre-condition:** được quyền truy cập. **Post-condition:** không thay đổi dữ liệu.
- **Main Flow:** RBAC + ownership → query bản ghi chưa xóa. **Alternative Flow:** employee/admin xem theo phạm vi rộng. **Exception:** không thấy/không quyền trả lỗi phù hợp.

### FR-007 — Xem lịch sử giao dịch/sao kê

- **Actor:** Customer/Employee/Admin. **Mô tả:** truy vấn ledger theo account và khoảng thời gian.
- **Input:** account, from/to, filter/sort/page. **Output:** debit, credit, balance sau từng dòng.
- **Pre-condition:** có quyền account. **Post-condition:** không đổi dữ liệu.
- **Main Flow:** query `transaction_entries` join `transactions`. **Alternative Flow:** yêu cầu export tạo job. **Exception:** khoảng thời gian sai bị reject.

### FR-008 — Quản lý người thụ hưởng

- **Actor:** Customer. **Mô tả:** CRUD mềm danh sách payee.
- **Input:** nickname, bank code, account number/name. **Output:** payee.
- **Pre-condition:** customer hợp lệ. **Post-condition:** dữ liệu thuộc customer, delete là soft-delete.
- **Main Flow:** validate → create/update/delete → audit. **Alternative Flow:** liên kết account nội bộ. **Exception:** payee trùng bị reject.

### FR-009 — Chuyển khoản nội bộ

- **Actor:** Customer. **Mô tả:** chuyển giữa hai account trong hệ thống.
- **Input:** source, destination, amount, description, idempotency key, OTP. **Output:** transaction status.
- **Pre-condition:** KYC `VERIFIED`, source ACTIVE và sở hữu, đủ số dư. **Post-condition:** hai balance và hai ledger entry nhất quán.
- **Main Flow:** validate → PENDING/OTP_REQUIRED → verify OTP → lock/recheck → debit/credit → SUCCESS → audit/notify.
- **Alternative Flow:** customer hủy trước xử lý → `CANCELLED`. **Exception:** thiếu tiền/OTP sai/lỗi DB → rollback và `FAILED` khi phù hợp.

### FR-010 — Chuyển khoản liên ngân hàng

- **Actor:** Customer, External Bank. **Mô tả:** chuyển tới account ngoài qua mock adapter.
- **Input:** source, snapshot thông tin đích, amount, OTP. **Output:** trạng thái giao dịch.
- **Pre-condition:** như FR-009; bank code/đích hợp lệ. **Post-condition:** debit ledger nếu gateway chấp nhận; giữ snapshot đích.
- **Main Flow:** validate → OTP → lock/recheck → gateway với idempotency → debit/SUCCESS.
- **Alternative Flow:** gateway từ chối → FAILED. **Exception:** timeout/không rõ kết quả giữ PROCESSING để đối soát, không retry mù.

### FR-011 — Xem và thanh toán hóa đơn

- **Actor:** Customer. **Mô tả:** thanh toán điện/nước/internet/điện thoại.
- **Input:** invoice, account, OTP. **Output:** payment và transaction.
- **Pre-condition:** KYC verified; invoice UNPAID; account đủ tiền. **Post-condition:** invoice PAID, debit ledger, payment/transaction SUCCESS.
- **Main Flow:** validate → create pending → OTP → lock account/invoice → debit → cập nhật đồng thời → notify.
- **Alternative Flow:** lần thử thất bại được giữ, có thể thử lại. **Exception:** chỉ tối đa một payment SUCCESS/invoice.

### FR-012 — OTP giao dịch/2FA

- **Actor:** user, Email/SMS adapter. **Mô tả:** OTP 6 số, phân biệt purpose.
- **Input:** user, purpose, target và code. **Output:** trạng thái verify.
- **Pre-condition:** action cần OTP. **Post-condition:** OTP dùng một lần hoặc bị khóa sau 5 lần.
- **Main Flow:** random code → lưu hash → expiry 5 phút → gửi → constant-time verify → consume.
- **Alternative Flow:** tạo lại làm vô hiệu challenge cũ theo cùng context. **Exception:** sai/hết hạn/đã dùng bị từ chối.

### FR-013 — Thông báo

- **Actor:** hệ thống/Customer. **Mô tả:** EMAIL và IN_APP cho các event nghiệp vụ.
- **Input:** user, event, template data. **Output:** notification status/read status.
- **Pre-condition:** event hợp lệ. **Post-condition:** bản ghi được lưu và có thể gửi async.
- **Main Flow:** tạo PENDING → adapter gửi → SENT/FAILED. **Alternative Flow:** in-app được đánh dấu read. **Exception:** lỗi gửi không rollback giao dịch tài chính đã commit.

### FR-014 — Báo cáo/dashboard/sao kê

- **Actor:** Customer/Employee/Admin. **Mô tả:** tổng balance/income/expense/count, phân loại/tháng, báo cáo hệ thống.
- **Input:** scope, period, filters. **Output:** dữ liệu tổng hợp hoặc job export.
- **Pre-condition:** RBAC/ownership. **Post-condition:** export được audit.
- **Main Flow:** query ledger/transaction → aggregate → trả kết quả. **Alternative Flow:** file lớn chạy background. **Exception:** giới hạn period/size không hợp lệ.

### FR-015 — Import dữ liệu

- **Actor:** Admin/Employee được cấp quyền. **Mô tả:** thiết kế hỗ trợ CSV/Excel customer/invoice.
- **Input:** file và mapping. **Output:** job, thống kê thành công/lỗi.
- **Pre-condition:** quyền import. **Post-condition:** dữ liệu hợp lệ được commit theo batch, có audit.
- **Main Flow:** upload → validate → job → import. **Alternative Flow:** dry-run. **Exception:** dòng lỗi được báo nhưng không lộ dữ liệu nhạy cảm.

### FR-016 — Quản lý user và soft delete/restore

- **Actor:** Admin. **Mô tả:** tìm kiếm, khóa, soft-delete, restore user/customer/account phù hợp.
- **Input:** id, action, reason. **Output:** trạng thái/version mới.
- **Pre-condition:** `users:manage`; không tự vô hiệu admin cuối cùng. **Post-condition:** audit đầy đủ.
- **Main Flow:** authorize → mutate → audit. **Alternative Flow:** restore nếu không xung đột unique/business rule. **Exception:** không hard-delete lịch sử tài chính.

### FR-017 — Audit log

- **Actor:** hệ thống/Admin. **Mô tả:** ghi và tra cứu hành vi bảo mật/nghiệp vụ.
- **Input:** actor, action, resource, before/after, IP, user-agent. **Output:** immutable audit event.
- **Pre-condition:** action cần audit. **Post-condition:** log không chứa secret/token/OTP/password.
- **Main Flow:** redact → append log → admin query/filter/export. **Alternative Flow:** actor null cho system event. **Exception:** lỗi audit với thao tác nhạy cảm phải được log ứng dụng và xử lý theo chính sách fail-safe.

### FR-018 — Background job

- **Actor:** user/Job Worker. **Mô tả:** theo dõi export/gửi email lớn.
- **Input:** job type, parameters, requester. **Output:** PENDING/PROCESSING/SUCCESS/FAILED và location.
- **Pre-condition:** requester có quyền. **Post-condition:** kết quả hoặc lỗi an toàn được lưu.
- **Main Flow:** create → enqueue → process → persist result → notify. **Alternative Flow:** retry có kiểm soát. **Exception:** worker crash để job có thể được recovery.

Mọi danh sách customers, accounts, transactions, payees, invoices, payments, audit logs, notifications phải hỗ trợ search/filter/sort/pagination theo allow-list; không cho client truyền tên cột SQL tùy ý.

## 7. Yêu cầu phi chức năng

- **NFR-001 Security:** Argon2/bcrypt cho password; chỉ lưu hash token/OTP; TLS ngoài local; least privilege; input validation; secret qua environment.
- **NFR-002 Token:** access token ngắn hạn; refresh token có expiry, rotation/revoke; không ghi token vào log.
- **NFR-003 Authorization:** kiểm tra RBAC và ownership ở service/repository, deny-by-default.
- **NFR-004 Performance:** API thông thường mục tiêu dưới 2 giây ở tải demo; danh sách bắt buộc pagination; index theo truy vấn chính.
- **NFR-005 Reliability:** transfer/payment dùng một DB transaction ACID, row lock và rollback đầy đủ.
- **NFR-006 Data integrity:** tiền dùng `NUMERIC(19,4)`/`Decimal`; FK/unique/check enforce tại DB.
- **NFR-007 Maintainability:** tách Router → Service → Repository → Model/Schema; integration qua adapter.
- **NFR-008 Scalability:** FastAPI stateless có thể scale ngang; Celery worker scale riêng; PostgreSQL là source of truth.
- **NFR-009 Logging:** application log có correlation ID tách biệt audit log; redact PII/secret.
- **NFR-010 Availability:** health/readiness kiểm tra phụ thuộc; lỗi external không làm mất trạng thái giao dịch.
- **NFR-011 Recovery:** backup/restore PostgreSQL được kiểm thử; migration có version; transaction/ledger không bị purge.
- **NFR-012 Usability:** lỗi có mã ổn định, thông điệp tiếng Việt rõ ràng nhưng không lộ chi tiết bảo mật.

## 8. Business Rules

- BR-001: chỉ CUSTOMER có KYC `VERIFIED` mới tạo transfer/payment.
- BR-002: amount > 0, fee >= 0, balance không âm; currency ISO 3 ký tự.
- BR-003: OTP gồm 6 chữ số ở tầng ứng dụng, hết hạn 5 phút, dùng một lần, tối đa 5 lần sai; DB chỉ lưu hash.
- BR-004: internal transfer có source/destination nội bộ khác nhau; interbank lưu snapshot đích ngoài.
- BR-005: transaction/payment hoàn tất không xóa; dùng FAILED/CANCELLED/REVERSAL.
- BR-006: một invoice có nhiều lần payment attempt nhưng tối đa một payment SUCCESS.
- BR-007: customers/accounts/invoices tăng `version` ở mỗi update để optimistic locking.
- BR-008: users/customers/accounts/payees/invoices dùng soft delete; dữ liệu tài chính bất biến theo nghiệp vụ.
- BR-009: số dư chỉ đổi cùng transaction tạo ledger entry; idempotency key chống gửi lặp.
- BR-010: khóa nhiều account theo thứ tự ID cố định để giảm deadlock.

## 9. Authentication & Authorization

Mỗi user giữ đúng một role; role nhận nhiều permission dạng `resource:action`. Access token mang user/session claims tối thiểu, nhưng quyền phải lấy/kiểm tra đáng tin cậy. Refresh/reset token chỉ lưu hash. Ownership bổ sung cho RBAC: CUSTOMER không thể đọc dữ liệu customer khác. EMPLOYEE không được gán/đổi ADMIN.

## 10. Data Requirements

PostgreSQL là nguồn dữ liệu chính. Timestamp dùng `TIMESTAMPTZ` và UTC. Tiền dùng `NUMERIC(19,4)`. `transactions` lưu ý định/trạng thái nghiệp vụ; `transaction_entries` lưu biến động từng account và snapshot balance để dựng sao kê. Audit snapshot dùng JSONB đã loại secret.

## 11. External Integration

External Bank Gateway và Email/SMS được đóng sau adapter và mock trong bài tập. Celery/Redis dành cho gửi email và sinh file lớn; DB `jobs` lưu trạng thái bền vững. Integration phải dùng timeout, correlation/idempotency và không giả định retry luôn an toàn.

## 12. Audit / Security

Ghi các sự kiện login, password reset, KYC, CRUD nhạy cảm, account lock, transfer/payment, import/export. Lưu actor, action, resource, before/after, thời gian, IP, user-agent, correlation ID. Trước khi ghi phải loại `password`, `password_hash`, JWT, refresh/reset token và OTP.

## 13. Error Handling

Phân nhóm validation (400/422), unauthenticated (401), forbidden (403), not found (404), conflict/version/idempotency (409), rate limit (429), dependency unavailable (503). Không trả stack trace hoặc nguyên nhân đăng nhập chi tiết. Mọi lỗi tài chính phải rollback; trạng thái external không chắc chắn giữ `PROCESSING` để đối soát.

## 14. Assumptions & Constraints

- Một user CUSTOMER có tối đa một customer profile; employee/admin không cần customer record.
- Một customer có nhiều account. VND là mặc định nhưng schema hỗ trợ currency khác.
- Gateway/email hiện dùng mock; không có core banking thật.
- Dữ liệu seed chỉ dùng local. Yêu cầu pháp lý, hạn mức và tỷ giá thực tế nằm ngoài bài tập.
- Giai đoạn hiện tại không triển khai API/business logic; model và migration là nền móng để review.
