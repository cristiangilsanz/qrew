import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.service.core.auth import get_admin_user
from com.qode.qrew.v1.service.core.database import get_db
from com.qode.qrew.v1.service.core.limiter import limiter
from com.qode.qrew.v1.service.models.user import KycStatus, User
from com.qode.qrew.v1.service.repositories.fingerprint import (
    DeviceFingerprintRepository,
)
from com.qode.qrew.v1.service.repositories.user import UserRepository
from com.qode.qrew.v1.service.schemas.admin import (
    AuditVerifyResponse,
    FingerprintAdminResponse,
    KycReviewRequest,
    KycReviewResponse,
    UserListResponse,
    UserSummaryResponse,
)
from com.qode.qrew.v1.service.services.audit import AuditService
from com.qode.qrew.v1.service.services.fingerprint import FingerprintService
from com.qode.qrew.v1.service.services.kyc_review import (
    KycReviewError,
    KycReviewService,
)
from com.qode.qrew.v1.service.services.notification import (
    NotificationDispatcher,
    build_notification_dispatcher,
)

router = APIRouter(prefix="/admin", tags=["admin"])


def _get_notification_service() -> NotificationDispatcher:
    return build_notification_dispatcher()


def get_fingerprint_service(
    db: AsyncSession = Depends(get_db),
) -> FingerprintService:
    """Build and return the fingerprint service."""
    return FingerprintService(DeviceFingerprintRepository(db), AuditService())


def get_kyc_review_service(
    db: AsyncSession = Depends(get_db),
    notifier: NotificationDispatcher = Depends(_get_notification_service),
) -> KycReviewService:
    """Build and return the KYC review service."""
    return KycReviewService(UserRepository(db), notifier, AuditService())


@router.get(
    "/audit/verify",
    response_model=AuditVerifyResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify the integrity of the audit event Merkle hash chain",
)
@limiter.limit("10/minute")  # type: ignore[misc]
async def audit_verify(
    request: Request,
    _admin: User = Depends(get_admin_user),
) -> AuditVerifyResponse:
    """Walk the audit chain from genesis and detect any tampered rows."""
    result = await AuditService().verify_chain()
    return AuditVerifyResponse(
        valid=result.valid,
        event_count=result.event_count,
        tampered_ids=result.tampered_ids,
    )


@router.post(
    "/kyc/{user_id}/review",
    response_model=KycReviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve or reject a pending KYC submission",
)
@limiter.limit("60/minute")  # type: ignore[misc]
async def kyc_review(
    request: Request,
    user_id: uuid.UUID,
    body: KycReviewRequest,
    _admin: User = Depends(get_admin_user),
    service: KycReviewService = Depends(get_kyc_review_service),
) -> KycReviewResponse:
    """Move a user's KYC status from pending to approved or rejected."""
    try:
        user = await service.review(user_id, body.action, body.reason)
        return KycReviewResponse(
            user_id=str(user.id),
            kyc_status=user.kyc_status,
            message=f"KYC {user.kyc_status} successfully.",
        )
    except KycReviewError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": exc.message, "field": exc.field},
        ) from exc


# ── Device fingerprinting ─────────────────────────────────────────────────────


@router.get(
    "/fingerprints/{fingerprint_hash}",
    response_model=FingerprintAdminResponse,
    status_code=status.HTTP_200_OK,
    summary="Look up all user accounts associated with a device fingerprint hash",
)
@limiter.limit("60/minute")  # type: ignore[misc]
async def get_fingerprint(
    request: Request,
    fingerprint_hash: str,
    _admin: User = Depends(get_admin_user),
    service: FingerprintService = Depends(get_fingerprint_service),
) -> FingerprintAdminResponse:
    """Return all user IDs that have reported the given fingerprint hash."""
    user_ids = await service.get_by_hash(fingerprint_hash)
    return FingerprintAdminResponse(
        fingerprint_hash=fingerprint_hash,
        user_ids=[str(uid) for uid in user_ids],
        account_count=len(user_ids),
    )


# ── User listing ──────────────────────────────────────────────────────────────


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
    """Return a paginated list of users with optional filters."""
    page = max(page, 1)
    page_size = 20 if page_size < 1 or page_size > 100 else page_size  # noqa: PLR2004
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
