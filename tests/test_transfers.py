from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.entities import Account, Customer, OtpCode


def create_transfer(client, headers, amount="500000"):
    source = client.get("/api/v1/accounts", headers=headers).json()[0]
    return client.post(
        "/api/v1/transfers",
        headers=headers,
        json={
            "source_account_id": source["id"],
            "destination_account_number": "1000000002",
            "bank_code": "OUR_BANK",
            "amount": amount,
            "description": "Test transfer",
        },
    )


def test_transfer_success_and_balances(client, customer_headers):
    source_before = client.get("/api/v1/accounts", headers=customer_headers).json()[0]
    admin_login = client.post("/api/v1/auth/login", json={"username": "admin", "password": "Admin@123"})
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    all_customers = client.get("/api/v1/admin/customers", headers=admin_headers).json()
    customer2 = next(item for item in all_customers if item["customer_code"] == "CUS000002")
    with SessionLocal() as session:
        destination_before = session.scalar(select(Account).where(Account.customer_id == customer2["id"]))
        destination_balance_before = destination_before.balance

    pending = create_transfer(client, customer_headers)
    assert pending.status_code == 201
    body = pending.json()
    completed = client.post(
        f"/api/v1/transfers/{body['transaction_id']}/verify-otp",
        headers=customer_headers,
        json={"otp": body["development_otp"]},
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "SUCCESS"
    source_after = client.get(f"/api/v1/accounts/{source_before['id']}/balance", headers=customer_headers).json()
    assert float(source_after["balance"]) == float(source_before["balance"]) - 500000
    with SessionLocal() as session:
        destination_after = session.scalar(select(Account).where(Account.account_number == "1000000002"))
        assert destination_after.balance == destination_balance_before + 500000


def test_transfer_insufficient_balance(client, customer_headers):
    response = create_transfer(client, customer_headers, "999999999999")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INSUFFICIENT_BALANCE"


def test_transfer_without_kyc(client, customer_headers):
    with SessionLocal.begin() as session:
        customer = session.scalar(select(Customer).where(Customer.customer_code == "CUS000001"))
        customer.kyc_status = "PENDING"
    response = create_transfer(client, customer_headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "KYC_NOT_VERIFIED"


def test_incorrect_otp(client, customer_headers):
    pending = create_transfer(client, customer_headers).json()
    response = client.post(
        f"/api/v1/transfers/{pending['transaction_id']}/verify-otp",
        headers=customer_headers,
        json={"otp": "000000" if pending["development_otp"] != "000000" else "111111"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_OTP"


def test_expired_otp(client, customer_headers):
    pending = create_transfer(client, customer_headers).json()
    with SessionLocal.begin() as session:
        otp = session.scalar(select(OtpCode).where(OtpCode.transaction_id == pending["transaction_id"]))
        otp.created_at = datetime.now(UTC) - timedelta(minutes=10)
        otp.expires_at = datetime.now(UTC) - timedelta(minutes=5)
    response = client.post(
        f"/api/v1/transfers/{pending['transaction_id']}/verify-otp",
        headers=customer_headers,
        json={"otp": pending["development_otp"]},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "OTP_EXPIRED"
