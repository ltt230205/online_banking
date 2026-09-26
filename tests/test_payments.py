def test_bill_payment(client, customer_headers):
    account = client.get("/api/v1/accounts", headers=customer_headers).json()[0]
    invoice = client.get("/api/v1/invoices", headers=customer_headers).json()[0]
    pending = client.post(
        "/api/v1/payments",
        headers=customer_headers,
        json={"invoice_id": invoice["id"], "account_id": account["id"]},
    )
    assert pending.status_code == 201
    body = pending.json()
    completed = client.post(
        f"/api/v1/payments/{body['payment_id']}/verify-otp",
        headers=customer_headers,
        json={"otp": body["development_otp"]},
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "SUCCESS"
    refreshed_invoice = client.get(f"/api/v1/invoices/{invoice['id']}", headers=customer_headers)
    assert refreshed_invoice.json()["status"] == "PAID"
