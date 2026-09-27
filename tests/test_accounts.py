def test_get_balance(client, customer_headers):
    account = client.get("/api/v1/accounts", headers=customer_headers).json()[0]
    response = client.get(f"/api/v1/accounts/{account['id']}/balance", headers=customer_headers)
    assert response.status_code == 200
    assert response.json()["account_number"] == "1000000001"
    assert response.json()["balance"] == "20000000.0000"
