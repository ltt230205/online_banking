# Hướng dẫn sử dụng và ý nghĩa các API

Tài liệu mô tả **những endpoint đã được triển khai** trong `app/main.py` và `app/api/routers/`, không bao gồm các chức năng mới chỉ có trong tài liệu thiết kế. API phục vụ ba vai trò: `CUSTOMER` (khách hàng), `EMPLOYEE` (nhân viên) và `ADMIN` (quản trị viên).

**Địa chỉ khi chạy local:** `http://localhost:8000`; đường dẫn nghiệp vụ bắt đầu bằng `/api/v1`. Xem giao diện tương tác tại `http://localhost:8000/docs`. Nếu đổi cổng API trong `.env`, thay `8000` tương ứng.

## 1. Cách đọc và gọi API

- Các endpoint ghi **Công khai** không cần token. Các endpoint còn lại cần header `Authorization: Bearer <access_token>` của đúng vai trò.
- `POST /api/v1/auth/login` nhận JSON; `POST /api/v1/auth/token` nhận form `application/x-www-form-urlencoded`. Hai endpoint đều trả `access_token`. Swagger dùng `/auth/token` cho nút **Authorize**, nhưng ẩn endpoint này khỏi danh sách hiển thị.
- Mã `id` trong các ví dụ là biến lấy từ response trước đó, **không phải ID cố định**. Dùng `{{base_url}}`, `{{admin_token}}`, `{{customer_token}}` trong Postman nếu muốn chạy lại kịch bản.
- Các thao tác `POST`, `PUT`, `DELETE` dưới đây ghi vào database. Chuyển khoản và thanh toán thành công sẽ đổi số dư thật trong database local; chỉ chạy với dữ liệu demo.

## 2. Danh mục và ý nghĩa của 30 endpoint

### Hệ thống và xác thực

| # | API | Quyền | Ý nghĩa |
|---:|---|---|---|
| 1 | `GET /` | Công khai | Trả tên ứng dụng, đường dẫn Swagger và OpenAPI để kiểm tra nhanh server đang chạy. |
| 2 | `GET /health` | Công khai | Kiểm tra ứng dụng **và kết nối PostgreSQL**; trả `database: connected` hoặc lỗi `503`. |
| 3 | `POST /api/v1/auth/register` | Công khai | Đăng ký user vai trò `CUSTOMER`, tạo hồ sơ khách hàng và yêu cầu KYC trạng thái `PENDING`; chưa tạo tài khoản ngân hàng. |
| 4 | `POST /api/v1/auth/login` | Công khai | Kiểm tra username/password JSON và cấp Bearer token để gọi API có bảo vệ. |
| 5 | `POST /api/v1/auth/token` | Công khai | Cấp token bằng form OAuth2 cho nút **Authorize** của Swagger; ẩn khỏi danh sách endpoint trong Swagger. |

### Quản trị và duyệt hồ sơ

| # | API | Quyền | Ý nghĩa |
|---:|---|---|---|
| 6 | `GET /api/v1/admin/customers` | ADMIN, EMPLOYEE | Liệt kê hồ sơ khách hàng; lọc bằng `kyc_status`, phân trang bằng `page`, `page_size`. Dùng để tìm hồ sơ chờ duyệt. |
| 7 | `PUT /api/v1/admin/customers/{customer_id}/kyc` | ADMIN, EMPLOYEE | Duyệt `VERIFIED` hoặc từ chối `REJECTED` hồ sơ KYC. Khi từ chối phải có `rejection_reason`; thao tác được ghi audit. |
| 8 | `POST /api/v1/admin/employees` | ADMIN | Tạo user vai trò `EMPLOYEE`, phục vụ nghiệp vụ xét duyệt và xem khách hàng/tài khoản. |
| 9 | `GET /api/v1/admin/users` | ADMIN | Liệt kê user toàn hệ thống (gồm khách hàng/nhân viên/quản trị), có phân trang. |
| 10 | `GET /api/v1/admin/accounts` | ADMIN, EMPLOYEE | Xem danh sách tài khoản ngân hàng chưa bị xóa mềm của toàn hệ thống, có phân trang. |
| 29 | `GET /api/v1/admin/reports/transactions` | ADMIN | Báo cáo toàn hệ thống: tổng số giao dịch, số thành công/thất bại và tổng tiền chuyển khoản thành công. |
| 30 | `GET /api/v1/admin/audit-logs` | ADMIN | Xem nhật ký thao tác (đăng nhập, KYC, tạo nhân viên, tạo/xóa người thụ hưởng, giao dịch), mới nhất trước. |

### Khách hàng, tài khoản và người thụ hưởng

| # | API | Quyền | Ý nghĩa |
|---:|---|---|---|
| 11 | `GET /api/v1/customers/me` | User đăng nhập có hồ sơ khách hàng | Xem hồ sơ của chính mình; số giấy tờ được che, chỉ hiện bốn ký tự cuối. |
| 12 | `GET /api/v1/accounts` | CUSTOMER | Liệt kê các tài khoản thuộc khách hàng đăng nhập, lấy `account_id` cho bước sau. |
| 13 | `GET /api/v1/accounts/{account_id}` | User đăng nhập | Xem thông tin một tài khoản; CUSTOMER chỉ xem được tài khoản của mình. |
| 14 | `GET /api/v1/accounts/{account_id}/balance` | User đăng nhập | Xem số dư hiện tại và đơn vị tiền của tài khoản được phép truy cập. |
| 15 | `GET /api/v1/payees` | CUSTOMER | Xem danh bạ người thụ hưởng của chính khách hàng. |
| 16 | `POST /api/v1/payees` | CUSTOMER | Lưu người thụ hưởng để dùng lại. `bank_name` được lưu dưới dạng `bank_code` viết hoa; nếu số tài khoản tồn tại trong hệ thống, response có `is_internal: true`. |
| 22 | `GET /api/v1/accounts/{account_id}/statement` | User đăng nhập | Sao kê các bút toán **thành công** của tài khoản trong khoảng `from_date`–`to_date`; mặc định 30 ngày gần nhất. |
| 28 | `DELETE /api/v1/payees/{payee_id}` | CUSTOMER | Xóa mềm người thụ hưởng của chính mình; response `204`, không có body. |

### Hóa đơn, chuyển khoản và thanh toán

| # | API | Quyền | Ý nghĩa |
|---:|---|---|---|
| 17 | `GET /api/v1/invoices` | CUSTOMER | Liệt kê hóa đơn của khách hàng; chọn hóa đơn `UNPAID` để thanh toán. |
| 18 | `GET /api/v1/invoices/{invoice_id}` | CUSTOMER | Xem chi tiết và xác nhận số tiền, trạng thái của một hóa đơn thuộc chính mình. |
| 19 | `POST /api/v1/transfers` | CUSTOMER | Khởi tạo chuyển khoản nội bộ hoặc liên ngân hàng. Kiểm tra KYC, tài khoản nguồn, số dư; tạo giao dịch `PENDING` và OTP, **chưa trừ tiền**. |
| 20 | `POST /api/v1/transfers/{transaction_id}/verify-otp` | CUSTOMER | Xác thực OTP và thực thi chuyển khoản: trừ tài khoản nguồn, cộng tài khoản đích nếu nội bộ, chuyển giao dịch thành `SUCCESS`. |
| 21 | `GET /api/v1/transactions` | User đăng nhập | Tra cứu giao dịch có phân trang và bộ lọc `type`, `status`, `from_date`, `to_date`; CUSTOMER chỉ thấy giao dịch liên quan tài khoản của mình. |
| 23 | `POST /api/v1/payments` | CUSTOMER | Khởi tạo thanh toán hóa đơn `UNPAID` bằng tài khoản của mình; tạo payment/giao dịch `PENDING` và OTP, **chưa trừ tiền**. |
| 24 | `POST /api/v1/payments/{payment_id}/verify-otp` | CUSTOMER | Xác thực OTP, trừ tiền, chuyển payment/giao dịch thành `SUCCESS` và hóa đơn thành `PAID`. |

### Báo cáo cá nhân

| # | API | Quyền | Ý nghĩa |
|---:|---|---|---|
| 25 | `GET /api/v1/reports/me/summary` | CUSTOMER | Tổng số dư, tổng thu, tổng chi và số **bút toán** thành công trên các tài khoản của khách hàng. |
| 26 | `GET /api/v1/reports/me/expenses-by-category` | CUSTOMER | Tổng các bút toán ghi nợ theo **loại giao dịch** (`BILL_PAYMENT`, `INTERNAL_TRANSFER`, v.v.), không phải danh mục hàng hóa. |
| 27 | `GET /api/v1/reports/me/monthly-expenses` | CUSTOMER | Tổng các bút toán ghi nợ theo tháng `YYYY-MM`. |

**Cách đếm:** 27 endpoint nghiệp vụ hiện trong Swagger + 2 endpoint hệ thống (`/`, `/health`) cũng hiện trong Swagger + 1 endpoint OAuth2 (`/api/v1/auth/token`) ẩn khỏi danh sách Swagger = **30 endpoint được triển khai**. Tài liệu này dùng từ “endpoint” cho từng cặp phương thức + đường dẫn.

## 3. Kịch bản sử dụng theo nghiệp vụ

### Kịch bản A — Khách hàng mới đăng ký và được duyệt KYC

1. Gọi `POST /api/v1/auth/register` với thông tin khách hàng duy nhất. Response `201` chứa `customer_id`, `kyc_status: PENDING`.
2. ADMIN/EMPLOYEE đăng nhập, gọi `GET /api/v1/admin/customers?kyc_status=PENDING`, tìm `customer_id` vừa tạo.
3. Gọi `PUT /api/v1/admin/customers/{customer_id}/kyc` với `{"status":"VERIFIED"}`. Nếu từ chối, gửi `{"status":"REJECTED","rejection_reason":"..."}`.
4. Khách hàng đăng nhập và gọi `GET /api/v1/customers/me` để xem kết quả.

**Điều kiện quan trọng:** đăng ký và duyệt KYC **không tự mở tài khoản ngân hàng**. Repo hiện không có endpoint công khai để tạo account; muốn thử chuyển khoản/thanh toán, sử dụng khách hàng có account từ dữ liệu seed. KYC phải là `VERIFIED` để tạo giao dịch.

### Kịch bản B — Khách hàng chuyển 100.000 VND cho tài khoản nội bộ

1. Đăng nhập bằng `POST /api/v1/auth/login`, lấy token CUSTOMER.
2. Gọi `GET /api/v1/accounts`, chọn tài khoản `ACTIVE`; gọi `/accounts/{id}/balance` để ghi số dư trước giao dịch.
3. Tùy chọn gọi `POST /api/v1/payees` để lưu người nhận; API chuyển khoản hiện **không nhận `payee_id`**, nên vẫn phải gửi `destination_account_number` và `bank_code`.
4. Gọi `POST /api/v1/transfers` với `bank_code: "OUR_BANK"` (hoặc `"LOCAL"`) và số tài khoản đích có thật. Lưu `transaction_id` và OTP nhận được ở môi trường development.
5. Gọi `POST /api/v1/transfers/{transaction_id}/verify-otp` với OTP của chính giao dịch đó. Chỉ sau bước này giao dịch thành công và số dư đổi.
6. Kiểm tra `GET /api/v1/transactions?type=INTERNAL_TRANSFER&status=SUCCESS`, `/accounts/{id}/balance` và `/accounts/{id}/statement`.

Chuyển liên ngân hàng dùng `bank_code` khác `OUR_BANK`/`LOCAL`; phần cổng ngân hàng ngoài trong repo hiện là **mô phỏng trả thành công**, không thực hiện giao dịch với ngân hàng thật.

### Kịch bản C — Thanh toán hóa đơn

1. Gọi `GET /api/v1/invoices`; chọn hóa đơn của mình có `status: UNPAID`. Gọi `GET /api/v1/invoices/{invoice_id}` để xác nhận số tiền.
2. Gọi `GET /api/v1/accounts` để lấy `account_id` của tài khoản `ACTIVE` đủ số dư.
3. Gọi `POST /api/v1/payments` với `invoice_id` và `account_id`; lưu `payment_id` cùng OTP **mới**. OTP chuyển khoản không dùng được cho thanh toán.
4. Gọi `POST /api/v1/payments/{payment_id}/verify-otp`. Kiểm tra hóa đơn chuyển `PAID`, số dư giảm, giao dịch xuất hiện trong lịch sử/sao kê.
5. Gọi ba API `/reports/me/...` để xem tổng quan, chi theo loại giao dịch và theo tháng.

Nếu không còn hóa đơn `UNPAID`, cần bổ sung dữ liệu mẫu trong database/seed trước khi chạy kịch bản; repo **không có endpoint tạo hóa đơn**. Không gửi lại OTP cho payment đã hoàn tất.

### Kịch bản D — Quản trị và kiểm tra sau giao dịch

ADMIN đăng nhập → xem `admin/users`, `admin/customers`, `admin/accounts` → có thể tạo EMPLOYEE bằng `admin/employees` → sau khi khách hàng giao dịch, xem `admin/reports/transactions` và `admin/audit-logs`. EMPLOYEE được xem danh sách khách hàng/tài khoản và xét duyệt KYC, nhưng không có quyền tạo nhân viên hay xem báo cáo/audit của ADMIN.

## 4. Request mẫu để thực hành

Các giá trị trong ngoặc nhọn `{{...}}` là biến Postman hoặc giá trị lấy từ response trước đó. Không dùng lại username/email/identity đã đăng ký.

```http
POST {{base_url}}/api/v1/auth/register
Content-Type: application/json

{"username":"demo_new_01","password":"Demo@1234","email":"demo_new_01@example.com","phone":"0901234567","full_name":"Nguyen Van Demo","date_of_birth":"2000-01-01","identity_number":"012345678901","address":"Ha Noi"}
```

```http
POST {{base_url}}/api/v1/auth/login
Content-Type: application/json

{"username":"customer1","password":"<mat_khau_seed_trong_cau_hinh>"}
```

```http
POST {{base_url}}/api/v1/payees
Authorization: Bearer {{customer_token}}
Content-Type: application/json

{"name":"Nguyen Van B","bank_name":"OUR_BANK","account_number":"1000000002","nickname":"Nguoi nhan demo"}
```

```http
POST {{base_url}}/api/v1/transfers
Authorization: Bearer {{customer_token}}
Content-Type: application/json

{"source_account_id":{{source_account_id}},"destination_account_number":"1000000002","bank_code":"OUR_BANK","amount":"100000.00","description":"Chuyen khoan demo"}
```

```http
POST {{base_url}}/api/v1/transfers/{{transaction_id}}/verify-otp
Authorization: Bearer {{customer_token}}
Content-Type: application/json

{"otp":"{{transfer_otp}}"}
```

```http
POST {{base_url}}/api/v1/payments
Authorization: Bearer {{customer_token}}
Content-Type: application/json

{"invoice_id":{{invoice_id}},"account_id":{{source_account_id}}}
```

```http
POST {{base_url}}/api/v1/payments/{{payment_id}}/verify-otp
Authorization: Bearer {{customer_token}}
Content-Type: application/json

{"otp":"{{payment_otp}}"}
```

Response của hai API khởi tạo có `status: PENDING` và ID tương ứng (`transaction_id` hoặc `payment_id`). `development_otp` chỉ được trả khi `APP_ENV=development`; OTP có hiệu lực **5 phút**, tối đa **5 lần nhập sai**. Không lưu OTP/token vào tài liệu hoặc commit lên Git.

## 5. Lưu ý khi kiểm thử

- `401` thường là thiếu/sai/hết hạn token; `403` là sai vai trò hoặc khách hàng chưa được KYC khi tạo giao dịch; `404` có thể là ID không tồn tại/không thuộc người gọi; `409` có thể do dữ liệu trùng, số dư thiếu, hóa đơn đã trả hoặc giao dịch đã hoàn tất; `422` thường là body/tham số không hợp lệ.
- Chỉ giao dịch `SUCCESS` có bút toán trong sao kê và báo cáo thu/chi. Khởi tạo `PENDING` không thay đổi số dư.
- `/reports/me/summary.transaction_count` đếm **bút toán giao dịch** trên tài khoản khách hàng, nên không nhất thiết bằng số giao dịch trong `/transactions`.
- `DELETE /payees/{id}` là xóa mềm: bản ghi vẫn có trong database để phục vụ lịch sử, nhưng không còn trong danh sách người thụ hưởng.
- Tài liệu thao tác kiểm thử đủ 30 endpoint theo đúng thứ tự và dữ liệu seed: [API_TEST_SCENARIO.md](API_TEST_SCENARIO.md). Giao diện Postman có thể dùng collection trong `postman/`.
