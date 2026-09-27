# Kịch bản kiểm thử toàn bộ API

Tài liệu này hướng dẫn gọi **đủ 30 endpoint đang được triển khai**: 27 endpoint nghiệp vụ hiển thị trong Swagger, 1 endpoint OAuth2 ẩn khỏi Swagger và 2 endpoint hệ thống. Kịch bản dùng database **local/demo**; chuyển tiền, thanh toán và xóa người thụ hưởng sẽ thay đổi dữ liệu. Không chạy trên môi trường production.

Nguồn endpoint thực tế: [`app/main.py`](../app/main.py) và [`app/api/routers/`](../app/api/routers/). Các luồng chỉ có trong tài liệu thiết kế nhưng chưa có router không nằm trong kịch bản này.

## 1. Chuẩn bị

Từ thư mục gốc của repo, chạy trong PowerShell:

```powershell
docker compose up --build -d
docker compose exec backend python -m app.seed
docker compose ps
```

Mở Swagger tại <http://localhost:8000/docs> (thay `8000` nếu `API_PORT` trong `.env` khác). Kiểm tra `GET /health` trước khi tiếp tục. Lệnh seed tạo 20 khách hàng đã KYC, tài khoản, người thụ hưởng và hóa đơn mẫu; nó không tự chạy khi chỉ khởi động backend bằng Docker.

Credential mặc định cho local, nếu chưa đổi các biến `SEED_*_PASSWORD` trong `.env`:

| Vai trò | Username | Password |
|---|---|---|
| ADMIN | `admin` | `Admin@123` |
| EMPLOYEE | `employee` | `Employee@123` |
| CUSTOMER | `customer1`…`customer20` | `Customer@123` |

Kịch bản dùng `customer1` làm người gửi/thanh toán. Tài khoản nguồn của họ có số `1000000001`; tài khoản đích `1000000002` thuộc `customer2`. **Không đoán ID**: lấy `account_id` từ `GET /api/v1/accounts`, vì ID database có thể khác giữa các lần cài đặt.

Để gọi API có bảo vệ trong Swagger, nhấn **Authorize**, nhập username/password của vai trò cần dùng. Swagger gọi `POST /api/v1/auth/token` ở phía sau. Sau bước 5, chọn lại `admin` cho bước 6–10; đổi sang `customer1` cho bước 11–28; rồi chọn lại `admin` cho bước 29–30. Nếu gọi bằng HTTP client khác, gửi `Authorization: Bearer <access_token>` tương ứng nhận được từ `/auth/login` hoặc `/auth/token`.

## 2. Trình tự gọi đủ 30 endpoint

Các biến cần ghi lại khi chạy: `new_customer_id` (bước 3), `source_account_id` (bước 12), `payee_id` (bước 16), `invoice_id` (bước 17), `transaction_id` (bước 19), `payment_id` (bước 23). Hai OTP ở bước 19 và 23 **khác nhau**.

| # | Vai trò | Method + endpoint | Thao tác và kết quả mong đợi |
|---:|---|---|---|
| 1 | Công khai | `GET /` | `200`; trả tên ứng dụng và đường dẫn tài liệu. |
| 2 | Công khai | `GET /health` | `200`; `database` là `connected`. Nếu `503`, kiểm tra PostgreSQL. |
| 3 | Công khai | `POST /api/v1/auth/register` | `201`; tạo khách hàng mới với KYC `PENDING`. Lưu `customer_id` thành `new_customer_id`. |
| 4 | Công khai | `POST /api/v1/auth/login` | `200`; đăng nhập `admin`, lưu `access_token` Admin. |
| 5 | Công khai | `POST /api/v1/auth/token` | `200`; đăng nhập `customer1` bằng **form**, lưu `access_token` Customer. Endpoint này ẩn khỏi danh sách Swagger nhưng được nút Authorize sử dụng. |
| 6 | Admin | `GET /api/v1/admin/customers?kyc_status=PENDING` | `200`; tìm khách hàng mới. Có thể tăng `page_size` nếu cần. |
| 7 | Admin | `PUT /api/v1/admin/customers/{new_customer_id}/kyc` | `200`; gửi `VERIFIED`, kiểm tra trạng thái KYC đã đổi. |
| 8 | Admin | `POST /api/v1/admin/employees` | `201`; tạo nhân viên demo với username/email chưa tồn tại. |
| 9 | Admin | `GET /api/v1/admin/users` | `200`; danh sách có nhân viên vừa tạo. Dùng `page`/`page_size` nếu chưa thấy. |
| 10 | Admin | `GET /api/v1/admin/accounts` | `200`; xem các tài khoản toàn hệ thống. |
| 11 | Customer1 | `GET /api/v1/customers/me` | `200`; chỉ trả hồ sơ của Customer1, số định danh được che bớt. |
| 12 | Customer1 | `GET /api/v1/accounts` | `200`; tìm tài khoản số `1000000001`, lưu `id` thành `source_account_id`. |
| 13 | Customer1 | `GET /api/v1/accounts/{source_account_id}` | `200`; xem chi tiết tài khoản nguồn. |
| 14 | Customer1 | `GET /api/v1/accounts/{source_account_id}/balance` | `200`; ghi lại số dư trước giao dịch. |
| 15 | Customer1 | `GET /api/v1/payees` | `200`; xem danh sách người thụ hưởng hiện có. |
| 16 | Customer1 | `POST /api/v1/payees` | `201`; thêm người thụ hưởng demo, lưu `id` thành `payee_id`. |
| 17 | Customer1 | `GET /api/v1/invoices` | `200`; chọn hóa đơn `UNPAID` của Customer1, lưu `id` thành `invoice_id`. |
| 18 | Customer1 | `GET /api/v1/invoices/{invoice_id}` | `200`; xác nhận hóa đơn đang `UNPAID` và ghi lại `amount`. |
| 19 | Customer1 | `POST /api/v1/transfers` | `201`; tạo chuyển khoản nội bộ 100.000 VND, lưu `transaction_id` và `development_otp`. |
| 20 | Customer1 | `POST /api/v1/transfers/{transaction_id}/verify-otp` | `200`; gửi OTP của bước 19, giao dịch chuyển sang `SUCCESS`. |
| 21 | Customer1 | `GET /api/v1/transactions?type=INTERNAL_TRANSFER&status=SUCCESS` | `200`; thấy giao dịch vừa hoàn tất. API hỗ trợ thêm `page`, `page_size`, `from_date`, `to_date`. |
| 22 | Customer1 | `GET /api/v1/accounts/{source_account_id}/statement` | `200`; thấy khoản ghi nợ của giao dịch. Mặc định lấy 30 ngày gần đây. |
| 23 | Customer1 | `POST /api/v1/payments` | `201`; tạo thanh toán hóa đơn, lưu `payment_id` và `development_otp` **mới**. |
| 24 | Customer1 | `POST /api/v1/payments/{payment_id}/verify-otp` | `200`; gửi OTP của bước 23, thanh toán chuyển sang `SUCCESS`. |
| 25 | Customer1 | `GET /api/v1/reports/me/summary` | `200`; xem tổng số dư, thu/chi và số giao dịch. |
| 26 | Customer1 | `GET /api/v1/reports/me/expenses-by-category` | `200`; xem chi tiêu theo danh mục. |
| 27 | Customer1 | `GET /api/v1/reports/me/monthly-expenses` | `200`; xem chi tiêu theo tháng. |
| 28 | Customer1 | `DELETE /api/v1/payees/{payee_id}` | `204`; xóa mềm người thụ hưởng vừa thêm. |
| 29 | Admin | `GET /api/v1/admin/reports/transactions` | `200`; xem tổng số giao dịch, số thành công/thất bại và tổng tiền chuyển. |
| 30 | Admin | `GET /api/v1/admin/audit-logs` | `200`; kiểm tra log đăng nhập, KYC, tạo nhân viên, người thụ hưởng, chuyển tiền và thanh toán. |

## 3. Request body mẫu

### Bước 3 — đăng ký khách hàng

Đổi `username`, `email`, `phone`, `identity_number` sang giá trị chưa có trong database nếu chạy lại.

```json
{
  "username": "demo_user_01",
  "password": "Demo@1234",
  "email": "demo_user_01@example.com",
  "phone": "0901234567",
  "full_name": "Nguyen Van Demo",
  "date_of_birth": "2000-01-01",
  "identity_number": "012345678901",
  "address": "Ha Noi"
}
```

Khách hàng vừa đăng ký có KYC `PENDING` và **chưa có tài khoản ngân hàng**. API hiện tại không có endpoint tạo tài khoản, nên phần chuyển tiền/thanh toán dùng `customer1` từ seed, không dùng khách hàng mới này.

### Bước 4 và 5 — lấy token

`POST /api/v1/auth/login` nhận JSON:

```json
{"username":"admin","password":"Admin@123"}
```

`POST /api/v1/auth/token` nhận `application/x-www-form-urlencoded`, **không phải JSON**. Nút Authorize của Swagger gọi endpoint này. Để gọi trực tiếp trong PowerShell:

```powershell
Invoke-RestMethod -Method Post -Uri 'http://localhost:8000/api/v1/auth/token' -ContentType 'application/x-www-form-urlencoded' -Body @{ username = 'customer1'; password = 'Customer@123' }
```

### Bước 7 — duyệt KYC

```json
{"status":"VERIFIED"}
```

### Bước 8 — tạo nhân viên

```json
{
  "username": "demo_employee_01",
  "password": "Employee@1234",
  "email": "demo_employee_01@example.com"
}
```

### Bước 16 — thêm người thụ hưởng

Đây là người thụ hưởng demo để thử API thêm/xóa. Chọn số tài khoản chưa được Customer1 lưu; nếu chạy lại sau khi xóa mềm, đổi số tài khoản vì ràng buộc unique vẫn còn.

```json
{
  "name": "Nguoi nhan demo",
  "bank_name": "DEMO",
  "account_number": "9900000003",
  "nickname": "Nguoi nhan thu nghiem"
}
```

### Bước 19 — chuyển tiền nội bộ

Thay `source_account_id` bằng ID thật lấy ở bước 12. `LOCAL` và `1000000002` biểu thị tài khoản nội bộ của Customer2.

```json
{
  "source_account_id": 1,
  "destination_account_number": "1000000002",
  "bank_code": "LOCAL",
  "amount": 100000,
  "description": "Demo chuyen tien noi bo"
}
```

### Bước 20 và 24 — xác thực OTP

```json
{"otp":"123456"}
```

Thay `123456` bằng `development_otp` **của đúng response** ở bước 19 hoặc 23. OTP hết hạn sau 5 phút, dùng một lần và tối đa 5 lần nhập sai. Trường `development_otp` chỉ có giá trị khi `APP_ENV=development`; môi trường khác không trả OTP trong response.

### Bước 23 — thanh toán hóa đơn

Thay cả hai ID bằng giá trị thật từ bước 17 và 12:

```json
{
  "invoice_id": 1,
  "account_id": 1
}
```

## 4. Đối chiếu kết quả cuối

Gọi lại những API đã dùng (không làm tăng số endpoint khác nhau):

1. `GET /api/v1/accounts/{source_account_id}/balance`: số dư nguồn giảm 100.000 VND cộng với tiền hóa đơn; phí chuyển khoản hiện là 0.
2. Đăng nhập `customer2`, gọi `GET /api/v1/accounts`: tìm tài khoản `1000000002`, rồi gọi `/balance`; số dư tài khoản đích tăng 100.000 VND.
3. Đăng nhập lại `customer1`, gọi `GET /api/v1/invoices/{invoice_id}`: trạng thái phải là `PAID`.
4. Gọi lại `GET /api/v1/payees`: người thụ hưởng đã xóa không còn trong danh sách.

Nếu cần chạy lại kịch bản từ đầu, dùng username/email/identity/phone mới, nhân viên mới và số tài khoản người thụ hưởng mới. Không gọi seed lại để “đặt lại” giao dịch: seed idempotent không hoàn tác các khoản chuyển hoặc thanh toán đã thực hiện.
