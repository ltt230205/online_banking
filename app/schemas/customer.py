from datetime import date, datetime

from pydantic import BaseModel, ConfigDict
from typing import Literal


class CustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    customer_code: str
    full_name: str
    date_of_birth: date
    identity_number: str
    phone: str
    address: str | None
    kyc_status: str
    kyc_verified_at: datetime | None
    version: int


class KycUpdateRequest(BaseModel):
    status: Literal["VERIFIED", "REJECTED"]
    rejection_reason: str | None = None
