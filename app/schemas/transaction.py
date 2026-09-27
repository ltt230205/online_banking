from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class TransferRequest(BaseModel):
    source_account_id: int
    destination_account_number: str = Field(min_length=3, max_length=34)
    bank_code: str = Field(min_length=2, max_length=20)
    amount: Decimal = Field(gt=0, max_digits=19, decimal_places=4)
    description: str | None = Field(default=None, max_length=500)


class OtpVerifyRequest(BaseModel):
    otp: str = Field(pattern=r"^\d{6}$")


class PendingActionResponse(BaseModel):
    transaction_id: int | None = None
    payment_id: int | None = None
    status: str
    message: str
    development_otp: str | None = None


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    transaction_code: str
    transaction_type: str
    status: str
    source_account_id: int | None
    destination_account_id: int | None
    destination_account_number: str | None
    destination_bank_code: str | None
    destination_account_name: str | None
    amount: Decimal
    fee: Decimal
    currency: str
    description: str | None
    created_at: datetime
    completed_at: datetime | None


class TransactionPage(BaseModel):
    items: list[TransactionResponse]
    page: int
    page_size: int
    total: int
