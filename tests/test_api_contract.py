"""Exercise every currently implemented business endpoint on the isolated test DB."""

from concurrent.futures import ThreadPoolExecutor
import asyncio
from uuid import uuid4

import pytest

from app.common.db import update_versioned, where
from app.db.session import AsyncSessionLocal
from app.repositories.customer_repository import CustomerRepository


def checked(response, status=200):
    assert response.status_code == status, response.text
    return response.json() if status != 204 else None


def login(client, username, password):
    token = checked(client.post("/api/v1/auth/login", json={"username": username, "password": password}))["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_all_business_endpoints(client):
    assert checked(client.get("/"))["docs"] == "/docs"
    assert checked(client.get("/health"))["database"] == "connected"
    suffix = uuid4().hex[:10]
    phone = "09" + str(int(suffix[:8], 16) % 100_000_000).zfill(8)
    registered = checked(client.post("/api/v1/auth/register", json={
        "username": f"scenario_{suffix}", "password": "Password@123", "email": f"scenario_{suffix}@example.com",
        "phone": phone, "full_name": "Scenario Customer", "date_of_birth": "2000-01-01",
        "identity_number": f"SCN{suffix}", "address": "Ha Noi",
    }), 201)
    admin = login(client, "admin", "Admin@123")
    customer = login(client, "customer1", "Customer@123")
    token_form = checked(client.post("/api/v1/auth/token", data={"username": "customer1", "password": "Customer@123"}))
    assert token_form["access_token"]

    pending_customers = checked(client.get("/api/v1/admin/customers?kyc_status=PENDING", headers=admin))
    assert registered["customer_id"] in [row["id"] for row in pending_customers]
    reviewed = checked(client.put(f"/api/v1/admin/customers/{registered['customer_id']}/kyc", headers=admin,
                                  json={"status": "VERIFIED"}))
    assert reviewed["kyc_status"] == "VERIFIED"
    checked(client.post("/api/v1/admin/employees", headers=admin, json={
        "username": f"staff_{suffix}", "password": "Password@123", "email": f"staff_{suffix}@example.com",
    }), 201)
    assert checked(client.get("/api/v1/admin/users?page_size=100", headers=admin))
    assert checked(client.get("/api/v1/admin/accounts", headers=admin))

    assert checked(client.get("/api/v1/customers/me", headers=customer))["customer_code"] == "CUS000001"
    account = checked(client.get("/api/v1/accounts", headers=customer))[0]
    account_id = account["id"]
    checked(client.get(f"/api/v1/accounts/{account_id}", headers=customer))
    checked(client.get(f"/api/v1/accounts/{account_id}/balance", headers=customer))
    checked(client.get("/api/v1/payees", headers=customer))
    payee = checked(client.post("/api/v1/payees", headers=customer, json={
        "name": "Scenario Payee", "bank_name": "OUR_BANK", "account_number": "1000000002",
        "nickname": "Scenario",
    }), 201)
    invoice = checked(client.get("/api/v1/invoices", headers=customer))[0]
    checked(client.get(f"/api/v1/invoices/{invoice['id']}", headers=customer))

    transfer = checked(client.post("/api/v1/transfers", headers=customer, json={
        "source_account_id": account_id, "destination_account_number": "1000000002",
        "bank_code": "OUR_BANK", "amount": "100000", "description": "Scenario transfer",
    }), 201)
    assert checked(client.post(f"/api/v1/transfers/{transfer['transaction_id']}/verify-otp", headers=customer,
                               json={"otp": transfer["development_otp"]}))["status"] == "SUCCESS"
    checked(client.get("/api/v1/transactions?status=SUCCESS", headers=customer))
    checked(client.get(f"/api/v1/accounts/{account_id}/statement", headers=customer))

    payment = checked(client.post("/api/v1/payments", headers=customer, json={
        "invoice_id": invoice["id"], "account_id": account_id,
    }), 201)
    assert checked(client.post(f"/api/v1/payments/{payment['payment_id']}/verify-otp", headers=customer,
                               json={"otp": payment["development_otp"]}))["status"] == "SUCCESS"
    assert checked(client.get(f"/api/v1/invoices/{invoice['id']}", headers=customer))["status"] == "PAID"
    checked(client.get("/api/v1/reports/me/summary", headers=customer))
    checked(client.get("/api/v1/reports/me/expenses-by-category", headers=customer))
    checked(client.get("/api/v1/reports/me/monthly-expenses", headers=customer))
    checked(client.delete(f"/api/v1/payees/{payee['id']}", headers=customer), 204)
    assert payee["id"] not in [row["id"] for row in checked(client.get("/api/v1/payees", headers=customer))]
    checked(client.get("/api/v1/admin/reports/transactions", headers=admin))
    checked(client.get("/api/v1/admin/audit-logs", headers=admin))


def test_concurrent_transfers_cannot_overdraw(client):
    customer = login(client, "customer1", "Customer@123")
    account = checked(client.get("/api/v1/accounts", headers=customer))[0]
    before = float(account["balance"])
    pending = [checked(client.post("/api/v1/transfers", headers=customer, json={
        "source_account_id": account["id"], "destination_account_number": "1000000002",
        "bank_code": "OUR_BANK", "amount": "15000000",
    }), 201) for _ in range(2)]

    def verify(item):
        return client.post(f"/api/v1/transfers/{item['transaction_id']}/verify-otp", headers=customer,
                           json={"otp": item["development_otp"]})

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(verify, pending))
    assert sorted(result.status_code for result in results) == [200, 409], [result.text for result in results]
    after = checked(client.get(f"/api/v1/accounts/{account['id']}/balance", headers=customer))
    assert float(after["balance"]) == before - 15_000_000


def test_concurrent_payments_charge_invoice_once(client):
    customer = login(client, "customer1", "Customer@123")
    account = checked(client.get("/api/v1/accounts", headers=customer))[0]
    invoice = checked(client.get("/api/v1/invoices", headers=customer))[0]
    before = float(account["balance"])
    pending = [checked(client.post("/api/v1/payments", headers=customer, json={
        "invoice_id": invoice["id"], "account_id": account["id"],
    }), 201) for _ in range(2)]

    def verify(item):
        return client.post(f"/api/v1/payments/{item['payment_id']}/verify-otp", headers=customer,
                           json={"otp": item["development_otp"]})

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(verify, pending))
    assert sorted(result.status_code for result in results) == [200, 409], [result.text for result in results]
    after = checked(client.get(f"/api/v1/accounts/{account['id']}/balance", headers=customer))
    assert float(after["balance"]) == before - float(invoice["amount"])


def test_version_guard_and_filter_whitelist():
    with pytest.raises(ValueError):
        where({"status; DROP TABLE users": "ACTIVE"}, {"status": "status"})

    async def stale_update_is_rejected():
        async with AsyncSessionLocal() as session:
            customer = await CustomerRepository(session).get_by_user_id(3)
            assert customer is not None
            result = await update_versioned(
                session, "customers", customer.id, customer.version + 1, {"kyc_status": "REJECTED"},
            )
            assert result is None
            await session.rollback()

    asyncio.run(stale_update_is_rejected())
