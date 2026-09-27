from decimal import Decimal

from pydantic import BaseModel


class PaymentRequest(BaseModel):
    invoice_id: int
    account_id: int


class PaymentResult(BaseModel):
    payment_id: int
    transaction_id: int
    status: str
    amount: Decimal
