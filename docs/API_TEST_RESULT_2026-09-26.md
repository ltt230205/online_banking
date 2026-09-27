# Kết quả chạy lại toàn bộ API trên database local — 2026-09-26

Đã gọi trực tiếp 30 endpoint theo `docs/API_TEST_SCENARIO.md` trên `http://127.0.0.1:8000`, đúng thứ tự nghiệp vụ. **29/30 endpoint đạt**. Ngoài ra, 3 lần gọi đọc lại dữ liệu sau luồng đều đạt.

| Bước | API | HTTP | Kết quả |
|---:|---|---:|---|
| 01 | `GET /` | 200 | Đạt |
| 02 | `GET /health` | 200 | Đạt; database connected |
| 03 | `POST /api/v1/auth/register` | 201 | Đạt |
| 04 | `POST /api/v1/auth/login` | 200 | Đạt |
| 05 | `POST /api/v1/auth/token` | 200 | Đạt |
| 06 | `GET /api/v1/admin/customers` | 200 | Đạt; thấy hồ sơ mới chờ KYC |
| 07 | `PUT /api/v1/admin/customers/{id}/kyc` | 200 | Đạt; VERIFIED |
| 08 | `POST /api/v1/admin/employees` | 201 | Đạt |
| 09 | `GET /api/v1/admin/users` | **500** | **Lỗi**; mong đợi 200 |
| 10 | `GET /api/v1/admin/accounts` | 200 | Đạt |
| 11 | `GET /api/v1/customers/me` | 200 | Đạt |
| 12 | `GET /api/v1/accounts` | 200 | Đạt |
| 13 | `GET /api/v1/accounts/{id}` | 200 | Đạt |
| 14 | `GET /api/v1/accounts/{id}/balance` | 200 | Đạt |
| 15 | `GET /api/v1/payees` | 200 | Đạt |
| 16 | `POST /api/v1/payees` | 201 | Đạt |
| 17 | `GET /api/v1/invoices` | 200 | Đạt |
| 18 | `GET /api/v1/invoices/{id}` | 200 | Đạt |
| 19 | `POST /api/v1/transfers` | 201 | Đạt |
| 20 | `POST /api/v1/transfers/{id}/verify-otp` | 200 | Đạt; SUCCESS |
| 21 | `GET /api/v1/transactions` | 200 | Đạt |
| 22 | `GET /api/v1/accounts/{id}/statement` | 200 | Đạt |
| 23 | `POST /api/v1/payments` | 201 | Đạt |
| 24 | `POST /api/v1/payments/{id}/verify-otp` | 200 | Đạt; SUCCESS |
| 25 | `GET /api/v1/reports/me/summary` | 200 | Đạt |
| 26 | `GET /api/v1/reports/me/expenses-by-category` | 200 | Đạt |
| 27 | `GET /api/v1/reports/me/monthly-expenses` | 200 | Đạt |
| 28 | `DELETE /api/v1/payees/{id}` | 204 | Đạt; xóa mềm người thụ hưởng demo |
| 29 | `GET /api/v1/admin/reports/transactions` | 200 | Đạt |
| 30 | `GET /api/v1/admin/audit-logs` | 200 | Đạt |

## Dữ liệu demo của lần chạy này

- Khách hàng `demo_3187915200`: user ID 99, customer ID 86, KYC `VERIFIED`.
- Nhân viên `employee_3187915200`: user ID 100.
- Người thụ hưởng demo: ID 83, đã xóa mềm sau khi test.
- Chuyển khoản nội bộ: transaction ID 7, 100.000 VND, `SUCCESS`.
- Hóa đơn ID 1: 750.000 VND, `PAID`; payment ID 1 `SUCCESS`.
- Tài khoản nguồn ID 1: số dư từ 20.000.000 xuống 19.150.000 VND, đúng bằng trừ 100.000 VND chuyển khoản và 750.000 VND thanh toán. Ba API đọc lại số dư, hóa đơn và danh sách người thụ hưởng đều trả 200 và khớp trạng thái database.

Không cần seed thêm tài khoản hay hóa đơn: trước khi chạy đã có 20 tài khoản và 20 hóa đơn chưa thanh toán. Lần chạy chỉ tạo dữ liệu demo cần thiết cho luồng trên.

## Lỗi bước 09

Log backend ghi `fastapi.exceptions.ResponseValidationError` với 22 lỗi ở trường `email`: các tài khoản seed có email dạng `@bank.local` (ví dụ `admin@bank.local`), trong khi `UserResponse.email` là `EmailStr`; Pydantic từ chối domain `.local` khi serialize danh sách. Đây là dữ liệu seed không tương thích schema phản hồi, không phải thiếu dữ liệu hay lỗi xác thực. Chưa thay đổi backend/seed trong lần kiểm thử này.

Chạy lại bằng `python scripts/test_all_api_demo.py` sẽ **tạo thêm dữ liệu và thực hiện thêm giao dịch demo**, không phải phép test chỉ đọc. File `postman/online_banking_all_30.postman_collection.json` chứa cùng 30 request để import vào Postman; lần chạy ghi ở đây được thực hiện trực tiếp qua HTTP local, không phải Collection Runner của Postman.

## Lần chạy thực tế trong Postman workspace Online banking

Collection **Online Banking - Full 30 API Test** đã được nhập vào Postman và chạy bằng **Local Collection Runner, 1 iteration** lúc 10:27:13 PM ngày 2026-09-26 (theo giờ hiển thị của Postman). Run này gửi đủ 30 request, ghi 34 assertions: 30 pass, 4 fail, 1 script error. Các lỗi được nhìn thấy trong tab **Runs**:

- Bước 09: HTTP 500 do email seed `@bank.local` không hợp lệ với `EmailStr` trong response.
- Bước 17: HTTP 200 nhưng script không tìm được hóa đơn `UNPAID` của `customer1`, vì hóa đơn duy nhất trước đó đã được thanh toán ở lần chạy trực tiếp.
- Bước 18, 23, 24: HTTP 422 do `invoice_id` không được bước 17 gán.

Đã bổ sung đúng một hóa đơn demo `INV-POSTMAN-20260926-01` cho `customer1` (invoice ID 83, 100.000 VND, ban đầu `UNPAID`). Sau đó gửi lại **ngay trong Postman**: bước 17 trả 200 và gán `invoice_id`; bước 18 trả 200; bước 23 trả 201, tạo payment ID 2; bước 24 trả 200 với `SUCCESS`. Gọi lại bước 18 cho thấy hóa đơn ID 83 là `PAID`; gọi lại bước 14 cho thấy số dư tài khoản nguồn là **18.950.000 VND**. Các lần gửi lại hiển thị trong **History** của Postman; chúng không sửa ngược thống kê của run đầu trong tab Runs.

Dữ liệu từ run Postman: khách hàng demo user ID 101/customer ID 87, nhân viên demo user ID 102, chuyển khoản transaction ID 9 `SUCCESS` (100.000 VND), payee demo ID 84 đã xóa mềm. Payment ID 2 tạo thêm transaction ID 10 `SUCCESS` (100.000 VND). Lượt chạy này còn **một lỗi backend chưa sửa ở API 09**.
