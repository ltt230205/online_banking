"""Run the 30 documented API checks against the local demo database.

This changes demo data: it registers a customer, creates an employee and payee,
executes a transfer and invoice payment, then soft-deletes the new payee.
"""

from __future__ import annotations

import json
import time
from decimal import Decimal
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "http://127.0.0.1:8000"
SUFFIX = str(time.time_ns())[-10:]
results: list[tuple[int, str, int | str, bool, str]] = []


def setting(key: str, fallback: str) -> str:
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith(key + "="):
                return line.partition("=")[2].strip().strip('"').strip("'")
    return fallback


def call(
    number: int,
    title: str,
    method: str,
    path: str,
    expected: int,
    *,
    token: str | None = None,
    body: dict | None = None,
    form: dict | None = None,
    critical: bool = False,
) -> object:
    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = "Bearer " + token
    payload = None
    if body is not None:
        payload = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    elif form is not None:
        payload = urlencode(form).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    request = Request(BASE_URL + path, data=payload, headers=headers, method=method)
    try:
        with urlopen(request, timeout=20) as response:
            status = response.status
            raw = response.read().decode("utf-8")
    except HTTPError as error:
        status = error.code
        raw = error.read().decode("utf-8", errors="replace")
    except URLError as error:
        status = "NETWORK"
        raw = str(error.reason)
    try:
        data = json.loads(raw) if raw else None
    except json.JSONDecodeError:
        data = raw
    ok = status == expected
    detail = "" if ok else str(data)[:160]
    results.append((number, title, status, ok, detail))
    print(f"{number:02d} {str(status):>7} {'PASS' if ok else 'FAIL'} {title}" + (f" | {detail}" if detail else ""), flush=True)
    if critical and not ok:
        raise RuntimeError(f"Cannot continue after step {number:02d}: {title}")
    return data


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> None:
    admin_password = setting("SEED_ADMIN_PASSWORD", "Admin@123")
    customer_password = setting("SEED_CUSTOMER_PASSWORD", "Customer@123")
    demo_password = "Demo@1234"
    employee_password = "DemoEmployee@1234"
    print(f"LOCAL demo run suffix={SUFFIX}", flush=True)

    call(1, "Root", "GET", "/", 200, critical=True)
    health = call(2, "Health", "GET", "/health", 200, critical=True)
    require(isinstance(health, dict) and health.get("database") == "connected", "Database not connected")
    registered = call(
        3, "Register demo customer", "POST", "/api/v1/auth/register", 201,
        body={"username": f"demo_{SUFFIX}", "password": demo_password,
              "email": f"demo_{SUFFIX}@example.com", "phone": f"09{SUFFIX}",
              "full_name": "Nguyen Van Demo", "date_of_birth": "2000-01-01",
              "identity_number": f"DEMO{SUFFIX}", "address": "Ha Noi"}, critical=True,
    )
    customer_id = registered["customer_id"]
    admin_login = call(4, "Login admin", "POST", "/api/v1/auth/login", 200,
                       body={"username": "admin", "password": admin_password}, critical=True)
    admin_token = admin_login["access_token"]
    customer_login = call(5, "OAuth2 token customer", "POST", "/api/v1/auth/token", 200,
                          form={"username": "customer1", "password": customer_password}, critical=True)
    customer_token = customer_login["access_token"]
    pending = call(6, "Admin customers pending", "GET",
                   "/api/v1/admin/customers?kyc_status=PENDING&page_size=100", 200,
                   token=admin_token, critical=True)
    require(any(item["id"] == customer_id for item in pending), "New customer absent from pending KYC list")
    reviewed = call(7, "Verify KYC", "PUT", f"/api/v1/admin/customers/{customer_id}/kyc", 200,
                    token=admin_token, body={"status": "VERIFIED"}, critical=True)
    require(reviewed["kyc_status"] == "VERIFIED", "KYC state was not VERIFIED")
    employee = call(8, "Create employee", "POST", "/api/v1/admin/employees", 201,
                    token=admin_token, body={"username": f"employee_{SUFFIX}",
                                             "password": employee_password,
                                             "email": f"employee_{SUFFIX}@example.com"}, critical=True)
    call(9, "Admin users", "GET", "/api/v1/admin/users?page=1&page_size=100", 200,
         token=admin_token)
    call(10, "Admin accounts", "GET", "/api/v1/admin/accounts?page=1&page_size=100", 200,
         token=admin_token)
    call(11, "Customer profile", "GET", "/api/v1/customers/me", 200,
         token=customer_token)
    accounts = call(12, "Customer accounts", "GET", "/api/v1/accounts", 200,
                    token=customer_token, critical=True)
    source = next((a for a in accounts if a["account_number"] == "1000000001"), None)
    require(source is not None, "Missing seeded source account 1000000001")
    account_id = source["id"]
    call(13, "Source account", "GET", f"/api/v1/accounts/{account_id}", 200,
         token=customer_token)
    before = call(14, "Source balance before", "GET",
                  f"/api/v1/accounts/{account_id}/balance", 200,
                  token=customer_token, critical=True)
    call(15, "Customer payees", "GET", "/api/v1/payees", 200, token=customer_token)
    payee = call(16, "Add demo payee", "POST", "/api/v1/payees", 201,
                 token=customer_token, body={"name": "Nguoi nhan demo", "bank_name": "DEMO",
                                             "account_number": f"99{SUFFIX}",
                                             "nickname": f"Test {SUFFIX}"}, critical=True)
    payee_id = payee["id"]
    invoices = call(17, "Customer invoices", "GET", "/api/v1/invoices", 200,
                    token=customer_token, critical=True)
    invoice = next((i for i in invoices if i["status"] == "UNPAID"), None)
    require(invoice is not None, "No unpaid invoice for customer1")
    invoice_id = invoice["id"]
    call(18, "Unpaid invoice", "GET", f"/api/v1/invoices/{invoice_id}", 200,
         token=customer_token)
    require(Decimal(str(before["balance"])) >= Decimal("100000") + Decimal(str(invoice["amount"])),
            "Insufficient demo balance for transfer plus invoice")

    transfer = call(19, "Create transfer", "POST", "/api/v1/transfers", 201,
                    token=customer_token,
                    body={"source_account_id": account_id,
                          "destination_account_number": "1000000002", "bank_code": "LOCAL",
                          "amount": 100000, "description": f"Full API demo {SUFFIX}"}, critical=True)
    require(transfer.get("development_otp"), "No development OTP returned for transfer")
    transaction_id = transfer["transaction_id"]
    verified_transfer = call(20, "Verify transfer OTP", "POST",
                             f"/api/v1/transfers/{transaction_id}/verify-otp", 200,
                             token=customer_token, body={"otp": transfer["development_otp"]},
                             critical=True)
    require(verified_transfer["status"] == "SUCCESS", "Transfer did not succeed")
    call(21, "Customer transactions", "GET",
         "/api/v1/transactions?type=INTERNAL_TRANSFER&status=SUCCESS", 200,
         token=customer_token)
    call(22, "Source statement", "GET", f"/api/v1/accounts/{account_id}/statement",
         200, token=customer_token)
    payment = call(23, "Create invoice payment", "POST", "/api/v1/payments", 201,
                   token=customer_token, body={"invoice_id": invoice_id, "account_id": account_id},
                   critical=True)
    require(payment.get("development_otp"), "No development OTP returned for payment")
    payment_id = payment["payment_id"]
    verified_payment = call(24, "Verify payment OTP", "POST",
                            f"/api/v1/payments/{payment_id}/verify-otp", 200,
                            token=customer_token, body={"otp": payment["development_otp"]},
                            critical=True)
    require(verified_payment["status"] == "SUCCESS", "Payment did not succeed")
    call(25, "Customer summary", "GET", "/api/v1/reports/me/summary", 200,
         token=customer_token)
    call(26, "Expenses by category", "GET", "/api/v1/reports/me/expenses-by-category",
         200, token=customer_token)
    call(27, "Monthly expenses", "GET", "/api/v1/reports/me/monthly-expenses",
         200, token=customer_token)
    call(28, "Delete demo payee", "DELETE", f"/api/v1/payees/{payee_id}", 204,
         token=customer_token)
    call(29, "Admin transaction report", "GET", "/api/v1/admin/reports/transactions",
         200, token=admin_token)
    call(30, "Admin audit logs", "GET", "/api/v1/admin/audit-logs?page=1&page_size=100",
         200, token=admin_token)

    after = call(31, "Postcheck source balance", "GET",
                 f"/api/v1/accounts/{account_id}/balance", 200, token=customer_token)
    paid_invoice = call(32, "Postcheck invoice", "GET",
                        f"/api/v1/invoices/{invoice_id}", 200, token=customer_token)
    remaining_payees = call(33, "Postcheck payee removed", "GET", "/api/v1/payees", 200,
                            token=customer_token)
    expected_balance = Decimal(str(before["balance"])) - Decimal("100000") - Decimal(str(invoice["amount"]))
    require(Decimal(str(after["balance"])) == expected_balance,
            f"Balance mismatch: expected {expected_balance}, got {after['balance']}")
    require(paid_invoice["status"] == "PAID", "Invoice did not become PAID")
    require(all(item["id"] != payee_id for item in remaining_payees), "Demo payee still listed")
    print(f"IDs customer={customer_id} employee={employee['id']} account={account_id} "
          f"payee={payee_id} invoice={invoice_id} transfer={transaction_id} payment={payment_id}",
          flush=True)
    print(f"BALANCE before={before['balance']} after={after['balance']} "
          f"invoice_amount={invoice['amount']}", flush=True)
    primary = [row for row in results if row[0] <= 30]
    print(f"SUMMARY {sum(row[3] for row in primary)}/{len(primary)} passed", flush=True)


if __name__ == "__main__":
    main()
