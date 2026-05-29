import uuid

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.service.core.auth.auth import get_admin_user
from com.qode.qrew.v1.service.core.infra.database import get_db
from com.qode.qrew.v1.service.core.infra.limiter import limiter
from com.qode.qrew.v1.service.models.auth.user import KycStatus, User
from com.qode.qrew.v1.service.repositories.auth.user import UserRepository
from com.qode.qrew.v1.service.schemas.admin.admin import (
    UserListResponse,
    UserSummaryResponse,
)
from com.qode.qrew.v1.service.services.auth.login_lockout import LoginLockoutService

from ._deps import get_login_lockout_service

router = APIRouter()

_DEFAULT_PAGE_SIZE = 20
_MAX_PAGE_SIZE = 100


@router.get(
    "/users",
    response_model=UserListResponse,
    status_code=status.HTTP_200_OK,
    summary="List and search users",
)
@limiter.limit("60/minute")  # type: ignore[misc]
async def list_users(
    request: Request,
    page: int = 1,
    page_size: int = 20,
    search: str | None = None,
    kyc_status: KycStatus | None = None,
    _admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> UserListResponse:
    """List and search users with optional filters."""
    page = max(page, 1)
    if page_size < 1 or page_size > _MAX_PAGE_SIZE:
        page_size = _DEFAULT_PAGE_SIZE
    repo = UserRepository(db)
    users, total = await repo.search_paginated(page, page_size, search, kyc_status)
    return UserListResponse(
        users=[
            UserSummaryResponse(
                id=u.id,
                email=u.email,
                full_name=u.full_name,
                kyc_status=u.kyc_status,
                email_verified=u.email_verified,
                phone_verified=u.phone_number_verified,
                is_admin=u.is_admin,
                created_at=u.created_at,
            )
            for u in users
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/users/{user_id}/unlock",
    status_code=status.HTTP_200_OK,
    summary="Clear a per-account login lockout",
)
@limiter.limit("30/minute")  # type: ignore[misc]
async def unlock_user(
    request: Request,
    user_id: uuid.UUID,
    admin: User = Depends(get_admin_user),
    lockout: LoginLockoutService = Depends(get_login_lockout_service),
) -> dict[str, str]:
    """Clear a per-account login lockout."""
    await lockout.admin_unlock(user_id, admin.id)
    return {"message": "User account unlocked."}
