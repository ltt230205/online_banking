# Entity Relationship Design

ERD: [diagrams/erd.mmd](diagrams/erd.mmd).

## Quyết định quan hệ

- Một `users` giữ một `roles`. Chỉ user CUSTOMER có tối đa một `customers`; Admin/Employee không cần customer record.
- Một customer có nhiều accounts, payees, invoices và KYC requests.
- `transactions` là giao dịch nghiệp vụ cấp cao; `transaction_entries` là sổ cái theo từng account.
- Internal transfer tham chiếu cả `source_account_id` và `destination_account_id`. Interbank để `destination_account_id=NULL` và lưu snapshot số tài khoản, bank code, tên người nhận để lịch sử không phụ thuộc dữ liệu ngoài thay đổi.
- Invoice : Payment là 1:N vì có thể thử thanh toán lại sau thất bại. Partial unique index bảo đảm tối đa một payment `SUCCESS`. Mỗi payment thành công liên kết tối đa một financial transaction.
- OTP luôn liên kết user; tùy purpose có thể liên kết transaction hoặc payment. Constraint không cho đồng thời cả hai target.
- Audit/notification liên kết user bằng `ON DELETE RESTRICT`; system audit cho phép actor null.

## Thiết kế transaction và statement

Không đặt một cặp `balance_before/balance_after` trực tiếp trên `transactions`: với internal transfer có hai account và hai cặp balance khác nhau. Thay vào đó:

- `transactions`: code, loại, trạng thái, source/destination, snapshot đích ngoài, amount, fee, mô tả và lifecycle.
- `transaction_entries`: một dòng DEBIT/CREDIT cho mỗi account bị tác động, chứa amount, `balance_before`, `balance_after` và timestamp.

Cách này tránh nhập nhằng, dựng sao kê chính xác và vẫn giữ `accounts.balance` như số dư hiện hành để đọc/lock nhanh. Nhược điểm là dữ liệu số dư được lặp có chủ đích và mọi cập nhật phải đi qua một transaction DB; constraint kiểm tra phép cộng/trừ giúp giảm sai lệch.

Với internal transfer chuẩn có hai entry: DEBIT nguồn và CREDIT đích. Interbank/payment có entry DEBIT nội bộ; trạng thái đối ứng bên ngoài nằm ở transaction/payment. Fee khi triển khai đầy đủ nên có transaction/entry FEE riêng hoặc được post thành entry rõ ràng, không âm thầm trừ khác với ledger.

## Kiểm tra mô hình

| Câu hỏi | Kết luận |
|---|---|
| User liên kết Customer? | Quan hệ 1–0/1 qua `customers.user_id UNIQUE`. |
| Employee cần Customer? | Không. Role nghiệp vụ và hồ sơ khách hàng độc lập. |
| Customer có nhiều Account? | Có, 1:N. |
| Account có nhiều Transaction? | Có qua source/destination và ledger entries. |
| Internal/Interbank biểu diễn ra sao? | Hai FK nội bộ; hoặc FK đích null + snapshot ngoài. |
| Payment liên kết Transaction? | 0/1 trong lúc pending; 1 khi đã post tài chính, FK unique. |
| Invoice–Payment? | 1:N attempts, tối đa một SUCCESS. |
| OTP liên kết gì? | User bắt buộc, transaction/payment tùy purpose. |
| Audit/Notification liên kết User? | FK RESTRICT; audit system cho phép null. |
| Soft delete? | users, customers, accounts, payees, invoices. |
| Versioning? | customers, accounts, invoices. Audit giữ snapshot thay đổi. |

## Data integrity và xóa

Tiền dùng `NUMERIC(19,4)`, không dùng FLOAT. Unique áp dụng username, email, identity, account/transaction/invoice/payment code. CHECK áp dụng amount/fee/balance/version/status/currency. FK tài chính dùng `RESTRICT`; không cascade xóa transaction, entry hay payment. Cascade chỉ dùng cho bảng nối RBAC không mang lịch sử nghiệp vụ.

## VARCHAR + CHECK thay PostgreSQL ENUM

Schema chọn `VARCHAR + CHECK`: dễ thêm trạng thái bằng migration, dễ rollback và tránh vòng đời type ENUM riêng của PostgreSQL. Đổi lại giá trị được lặp trong model/migration và cần test đồng bộ. PostgreSQL ENUM phù hợp khi tập giá trị cực kỳ ổn định; các lifecycle của bài tập có khả năng mở rộng nên CHECK hợp lý hơn.

## Versioning và lịch sử

Optimistic locking dùng `version > 0`, update theo `WHERE id=:id AND version=:expected`, đồng thời `version=version+1`. Không tạo history table riêng để tránh over-engineering; audit log lưu before/after JSONB cho thay đổi nhạy cảm. Audit không thay thế ledger và không được dùng để tính số dư.
