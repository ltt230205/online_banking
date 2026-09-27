from datetime import date

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=128)
    email: EmailStr
    phone: str = Field(min_length=9, max_length=20)
    full_name: str = Field(min_length=2, max_length=150)
    date_of_birth: date
    identity_number: str = Field(min_length=6, max_length=30)
    address: str | None = Field(default=None, max_length=1000)

    @field_validator("password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        if not any(char.isupper() for char in value) or not any(char.islower() for char in value):
            raise ValueError("Password must contain uppercase and lowercase letters")
        if not any(char.isdigit() for char in value):
            raise ValueError("Password must contain a digit")
        return value


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RegisterResponse(BaseModel):
    user_id: int
    customer_id: int
    username: str
    kyc_status: str


class EmployeeCreateRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)
    email: EmailStr


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: EmailStr
    status: str
    created_at: datetime
