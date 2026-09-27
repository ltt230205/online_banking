# Data Access Layer kiểu micro-ORM

Ứng dụng vẫn dùng SQLAlchemy để tạo `AsyncEngine`/`AsyncSession` và thực thi câu SQL, nhưng **không dùng ORM model để CRUD**. Alembic và các SQLAlchemy Declarative model trong `app/models/` được giữ để mô tả/kiểm tra schema hiện hữu; runtime API không trả ORM object từ repository.

## Luồng phụ thuộc

`Router → Service → Repository → app/common/db.py → PostgreSQL`

- `app/api/dependencies.py` cấp một `AsyncSession` cho request và rollback khi có lỗi.
- `app/services/` kiểm tra nghiệp vụ, phối hợp nhiều repository và quyết định thời điểm `commit`.
- `app/repositories/` chứa SQL thuần (`SELECT`, `INSERT`, `UPDATE`) cùng tham số bind `:name`; kết quả được ánh xạ sang các `@dataclass(frozen=True)` trong `app/repositories/rows.py`. Repository không commit.
- `app/common/db.py` tập trung `query`, `query_one`, `scalar`, `execute`, `where` và `update_versioned`.

Ví dụ trong `AccountRepository`, `SELECT a.* ... WHERE a.id=:id` nhận `id` qua mapping tham số; không ghép giá trị do người dùng nhập vào chuỗi SQL. Các phần SQL động như cột filter và bảng/cột update chỉ lấy từ whitelist cố định trong code.

## Transaction và khóa

Chuyển khoản và thanh toán tạo đối tượng `PENDING`, sau đó OTP được xác thực trong request riêng. Khi thực thi, service khóa các dòng liên quan bằng `FOR UPDATE`, kiểm tra lại số dư/trạng thái, cập nhật `accounts.balance` và `version` bằng `UPDATE ... WHERE version=:expected_version`, ghi ledger, cập nhật giao dịch/hóa đơn rồi mới `commit`. Nếu một bước lỗi, dependency rollback toàn bộ transaction đang mở. Hai request cạnh tranh không được trừ tiền hai lần.

Schema hiện tại gọi cột optimistic locking là `version` (không phải `row_version`); `update_versioned()` dùng cột này, nên **không cần migration**. Soft delete vẫn cập nhật `is_deleted`, `deleted_at`, `deleted_by` thay vì xóa vật lý.

## Kiểm thử

Test chạy trên một database test tách biệt và seed lại trước từng case. Có thể chọn tên database test mới để không chạm database test đang có:

```powershell
$env:TEST_POSTGRES_DB='online_banking_test_micro_local'
python -m pytest -q
```

`tests/test_api_contract.py` đi qua tất cả endpoint nghiệp vụ, kiểm tra hai chuyển khoản cạnh tranh cùng số dư, hai payment cạnh tranh cùng hóa đơn, whitelist filter và version conflict. `alembic check` xác nhận không có thay đổi schema.
