from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PayeeCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    bank_name: str = Field(min_length=2, max_length=20)
    account_number: str = Field(min_length=3, max_length=34)
    nickname: str | None = Field(default=None, max_length=100)


class PayeeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nickname: str
    account_number: str
    account_name: str
    bank_code: str
    is_internal: bool
    created_at: datetime
