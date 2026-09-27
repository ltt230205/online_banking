from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.models.entities import User
from app.schemas.customer import CustomerResponse
from app.services.customer_service import CustomerService, mask_identity


router = APIRouter(prefix="/customers", tags=["Customers"])


@router.get("/me", response_model=CustomerResponse)
def get_me(user: User = Depends(get_current_user), session: Session = Depends(get_db)) -> CustomerResponse:
    customer = CustomerService(session).get_for_user(user.id)
    result = CustomerResponse.model_validate(customer)
    return result.model_copy(update={"identity_number": mask_identity(customer.identity_number)})
