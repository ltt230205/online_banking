from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.schemas.auth import LoginRequest, RegisterRequest, RegisterResponse, TokenResponse
from app.services.auth_service import AuthService


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=RegisterResponse, status_code=201)
def register(data: RegisterRequest, session: Session = Depends(get_db)) -> RegisterResponse:
    user, customer = AuthService(session).register(data)
    return RegisterResponse(
        user_id=user.id,
        customer_id=customer.id,
        username=user.username,
        kyc_status=customer.kyc_status,
    )


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, session: Session = Depends(get_db)) -> TokenResponse:
    return TokenResponse(access_token=AuthService(session).login(data))


@router.post("/token", response_model=TokenResponse, include_in_schema=False)
def oauth2_token(form: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_db)) -> TokenResponse:
    return TokenResponse(access_token=AuthService(session).login(LoginRequest(username=form.username, password=form.password)))
