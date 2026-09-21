# Online Banking API

Bộ khởi tạo môi trường phát triển với Python 3.12, FastAPI và PostgreSQL 17.

## Chạy bằng Docker

Mở Docker Desktop, chọn Linux containers, sau đó chạy trong thư mục dự án:

```powershell
Copy-Item .env.example .env
docker compose up --build -d
docker compose ps
```

Nếu đã có `.env`, giữ lại cấu hình hiện tại. Mật khẩu mẫu chỉ dùng để phát triển local.

- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- Kiểm tra database: http://localhost:8000/health
- PostgreSQL: `localhost:5433`, tên database và tài khoản lấy từ `.env`.

API đợi PostgreSQL sẵn sàng trước khi khởi động. Trong Docker, API kết nối tới
host `db` và cổng `5432`; khi chạy Python local, API đọc host/port từ `.env`.

```powershell
docker compose logs -f api db
docker compose down
```

Dữ liệu được lưu trong volume `postgres_data` và được giữ khi chạy `docker compose down`.
Biến `POSTGRES_*` khởi tạo tài khoản/database khi volume còn trống; sửa `.env`
không tự đổi tài khoản của database đã có dữ liệu.

## Chạy FastAPI bằng Python local

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
# Tạo .env từ .env.example nếu chưa có.
docker compose up -d db
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Không chạy đồng thời API local và API Docker trên cùng cổng. Nếu đã chạy API Docker,
dùng `docker compose stop api` trước khi khởi động API local.

`requirements.txt` chứa các thư viện; `requirement.txt` là file tương thích với
cách viết số ít và có thể dùng cùng `pip install -r requirement.txt`.
Không commit `.env` hoặc `.venv`.

Tham khảo: [FastAPI Docker](https://fastapi.tiangolo.com/deployment/docker/),
[PostgreSQL Docker image](https://hub.docker.com/_/postgres).
