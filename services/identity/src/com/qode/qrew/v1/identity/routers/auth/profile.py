from datetime import datetime

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.identity.routers import Page, clamp_limit, cursor_paginate
from com.qode.qrew.v1.identity.services.auth.auth import (
    get_current_user,
    get_setup_or_full_user,
)
from com.qode.qrew.v1.identity.core.database import get_db
from com.qode.qrew.v1.identity.core.dependencies import limiter
from com.qode.qrew.v1.identity.models.audit.audit import AuditEvent
from com.qode.qrew.v1.identity.models.auth.user import User
from com.qode.qrew.v1.identity.routers.auth._deps.profile import get_profile_service
from com.qode.qrew.v1.identity.schemas.audit.audit import UserAuditEventResponse
from com.qode.qrew.v1.identity.schemas.auth.auth import (
    OnboardingStatusResponse,
    UserProfileResponse,
)
from com.qode.qrew.v1.identity.services.auth.profile import ProfileService

router = APIRouter()

_AUDIT_PAGE_SIZE = 50


@router.get(
    "/me",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Return the current user's profile",
)
@limiter.limit("60/minute")  # type: ignore[misc]
async def get_me(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> UserProfileResponse:
    """Return the current user's profile."""
    return UserProfileResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        phone_number=current_user.phone_number,
        kyc_status=current_user.kyc_status,
        email_verified=current_user.email_verified,
        phone_verified=current_user.phone_number_verified,
        created_at=current_user.created_at,
    )


@router.get(
    "/onboarding-status",
    response_model=OnboardingStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Return which onboarding steps the user has completed",
)
@limiter.limit("60/minute")  # type: ignore[misc]
async def get_onboarding_status(
    request: Request,
    current_user: User = Depends(get_setup_or_full_user),
    profile_svc: ProfileService = Depends(get_profile_service),
) -> OnboardingStatusResponse:
    """Return which onboarding steps the user has completed."""
    return await profile_svc.get_onboarding_status(current_user)


@router.get(
    "/audit",
    response_model=Page[UserAuditEventResponse],
    status_code=status.HTTP_200_OK,
    summary="Return the current user's audit history",
)
@limiter.limit("60/minute")  # type: ignore[misc]
async def list_user_audit(
    request: Request,
    action: str | None = None,
    since: datetime | None = None,
    cursor: str | None = None,
    limit: int = _AUDIT_PAGE_SIZE,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    profile_svc: ProfileService = Depends(get_profile_service),
) -> Page[UserAuditEventResponse]:
    """Return the current user's audit history."""
    page_limit = clamp_limit(limit, default=_AUDIT_PAGE_SIZE)
    stmt = profile_svc.query_user_audit(current_user.id, action=action, since=since)
    events, next_cursor = await cursor_paginate(
        db,
        stmt,
        sort_column=AuditEvent.created_at,
        id_column=AuditEvent.id,
        limit=page_limit,
        cursor=cursor,
    )
    return Page[UserAuditEventResponse](
        items=[UserAuditEventResponse.from_event(e) for e in events],
        next_cursor=next_cursor,
    )
