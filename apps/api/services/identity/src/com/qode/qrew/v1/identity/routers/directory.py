import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.identity.core.database import get_db
from com.qode.qrew.v1.identity.core.dependencies import verify_internal_key
from com.qode.qrew.v1.identity.repositories.user import UserRepository

router = APIRouter(
    prefix="/_internal/users",
    include_in_schema=False,
    dependencies=[Depends(verify_internal_key)],
)


class _LookupRequest(BaseModel):
    email: EmailStr


class _LookupResponse(BaseModel):
    user_id: uuid.UUID


@router.post("/lookup", response_model=_LookupResponse)
async def lookup_user(body: _LookupRequest, db: AsyncSession = Depends(get_db)) -> _LookupResponse:
    """Resolves an email address to the identifier of its holder."""
    user = await UserRepository(db).get_by_email(str(body.email))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown user")
    return _LookupResponse(user_id=user.id)
