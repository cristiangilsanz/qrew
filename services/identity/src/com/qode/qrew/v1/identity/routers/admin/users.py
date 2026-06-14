import uuid

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.identity.routers import Page, clamp_limit, cursor_paginate
from com.qode.qrew.v1.identity.services.auth.auth import get_admin_user
from com.qode.qrew.v1.identity.database import get_db
from com.qode.qrew.v1.identity.services.infra.limiter import limiter
from com.qode.qrew.v1.identity.models.auth.user import KycStatus, User
from com.qode.qrew.v1.identity.repositories.auth.user import UserRepository
from com.qode.qrew.v1.identity.schemas.admin.admin import UserSummaryResponse
from com.qode.qrew.v1.identity.services.auth.login_lockout import LoginLockoutService

from ._deps import get_login_lockout_service

router = APIRouter()

_DEFAULT_LIMIT = 20


@router.get(
    "/users",
    response_model=Page[UserSummaryResponse],
    status_code=status.HTTP_200_OK,
    summary="List and search users",
)
@limiter.limit("60/minute")  # type: ignore[misc]
async def list_users(
    request: Request,
    cursor: str | None = None,
    limit: int = _DEFAULT_LIMIT,
    search: str | None = None,
    kyc_status: KycStatus | None = None,
    _admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> Page[UserSummaryResponse]:
    """List and search users, newest first."""
    page_limit = clamp_limit(limit, default=_DEFAULT_LIMIT)
    repo = UserRepository(db)
    stmt = repo.search_query(search=search, kyc_status=kyc_status)
    users, next_cursor = await cursor_paginate(
        db,
        stmt,
        sort_column=User.created_at,
        id_column=User.id,
        limit=page_limit,
        cursor=cursor,
    )
    return Page[UserSummaryResponse](
        items=[
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
        next_cursor=next_cursor,
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
