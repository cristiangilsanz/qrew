from datetime import datetime

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.identity.core.api import Page, clamp_limit, cursor_paginate
from com.qode.qrew.v1.identity.core.auth.auth import (
    get_current_user,
    get_setup_or_full_user,
)
from com.qode.qrew.v1.identity.core.infra.database import get_db
from com.qode.qrew.v1.identity.core.infra.limiter import limiter
from com.qode.qrew.v1.identity.models.audit.audit import AuditEvent
from com.qode.qrew.v1.identity.models.auth.user import KycStatus, User
from com.qode.qrew.v1.identity.repositories.audit.audit import AuditRepository
from com.qode.qrew.v1.identity.repositories.passkey.passkey import (
    PasskeyCredentialRepository,
)
from com.qode.qrew.v1.identity.schemas.audit.audit import UserAuditEventResponse
from com.qode.qrew.v1.identity.schemas.auth.auth import (
    OnboardingStatusResponse,
    UserProfileResponse,
)

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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_setup_or_full_user),
) -> OnboardingStatusResponse:
    """Return which onboarding steps the user has completed."""
    passkey_repo = PasskeyCredentialRepository(db)
    has_passkey = await passkey_repo.has_passkey(current_user.id)
    kyc_submitted = current_user.kyc_status != KycStatus.not_submitted
    email_verified = current_user.email_verified
    phone_verified = current_user.phone_number_verified
    is_complete = email_verified and phone_verified and kyc_submitted and has_passkey
    return OnboardingStatusResponse(
        email_verified=email_verified,
        phone_verified=phone_verified,
        kyc_submitted=kyc_submitted,
        passkey_registered=has_passkey,
        is_complete=is_complete,
    )


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
) -> Page[UserAuditEventResponse]:
    """Return the current user's audit history."""
    page_limit = clamp_limit(limit, default=_AUDIT_PAGE_SIZE)
    repo = AuditRepository(db)
    stmt = repo.query_for_user(current_user.id, action=action, since=since)
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
