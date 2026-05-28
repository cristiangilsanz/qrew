import base64
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.service.core.auth.auth import (
    get_current_user,
    get_setup_or_full_user,
)
from com.qode.qrew.v1.service.core.infra.database import get_db
from com.qode.qrew.v1.service.core.infra.limiter import limiter
from com.qode.qrew.v1.service.models.auth.user import KycStatus, User
from com.qode.qrew.v1.service.repositories.audit.audit import AuditRepository
from com.qode.qrew.v1.service.repositories.passkey.passkey import (
    PasskeyCredentialRepository,
)
from com.qode.qrew.v1.service.schemas.audit.audit import (
    UserAuditCursor,
    UserAuditEventResponse,
    UserAuditListResponse,
)
from com.qode.qrew.v1.service.schemas.auth.auth import (
    OnboardingStatusResponse,
    UserProfileResponse,
)

router = APIRouter()

_AUDIT_PAGE_SIZE = 50


def _decode_audit_cursor(raw: str | None) -> tuple[datetime, uuid.UUID] | None:
    if raw is None:
        return None
    try:
        decoded = base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)).decode()
        parsed = UserAuditCursor.model_validate_json(decoded)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Invalid cursor", "field": "cursor"},
        ) from exc
    return parsed.created_at, parsed.id


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
    response_model=UserAuditListResponse,
    status_code=status.HTTP_200_OK,
    summary="Return the current user's audit history",
)
@limiter.limit("60/minute")  # type: ignore[misc]
async def list_user_audit(
    request: Request,
    action: str | None = None,
    since: datetime | None = None,
    cursor: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserAuditListResponse:
    """Return the current user's audit history."""
    cursor_pair = _decode_audit_cursor(cursor)
    cursor_created_at = cursor_pair[0] if cursor_pair else None
    cursor_id = cursor_pair[1] if cursor_pair else None
    repo = AuditRepository(db)
    events = await repo.list_for_user(
        current_user.id,
        limit=_AUDIT_PAGE_SIZE + 1,
        action=action,
        since=since,
        cursor_created_at=cursor_created_at,
        cursor_id=cursor_id,
    )
    next_cursor = None
    if len(events) > _AUDIT_PAGE_SIZE:
        last_visible = events[_AUDIT_PAGE_SIZE - 1]
        events = events[:_AUDIT_PAGE_SIZE]
        next_cursor = UserAuditCursor(
            created_at=last_visible.created_at, id=last_visible.id
        )
    return UserAuditListResponse(
        events=[UserAuditEventResponse.from_event(e) for e in events],
        next_cursor=next_cursor,
    )
