from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class InvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    invoice_code: str
    provider_code: str
    service_type: str
    customer_reference: str
    billing_period: str | None
    amount: Decimal
    currency: str
    due_date: date
    status: str
    paid_at: datetime | None
