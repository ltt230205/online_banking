from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db
from app.repositories.rows import UserRow
from app.schemas.customer import CustomerResponse
from app.services.customer_service import CustomerService, mask_identity


router = APIRouter(prefix="/customers", tags=["Customers"])


@router.get("/me", response_model=CustomerResponse)
async def get_me(user: UserRow = Depends(get_current_user), session: AsyncSession = Depends(get_db)) -> CustomerResponse:
    customer = await CustomerService(session).get_for_user(user.id)
    result = CustomerResponse.model_validate(customer)
    return result.model_copy(update={"identity_number": mask_identity(customer.identity_number)})
