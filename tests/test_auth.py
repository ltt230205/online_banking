from uuid import uuid4


def test_register(client):
    suffix = uuid4().hex[:8]
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": f"new_{suffix}",
            "password": "Password@123",
            "email": f"new_{suffix}@example.com",
            "phone": f"098{suffix[:7]}",
            "full_name": "Nguyễn Văn Mới",
            "date_of_birth": "2000-01-01",
            "identity_number": f"NEW{suffix}",
            "address": "Hà Nội",
        },
    )
    assert response.status_code == 201
    assert response.json()["kyc_status"] == "PENDING"


def test_login(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "customer1", "password": "Customer@123"},
    )
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]


def test_permission_denied(client, customer_headers):
    response = client.get("/api/v1/admin/reports/transactions", headers=customer_headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"
