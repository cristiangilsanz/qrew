from fastapi import APIRouter, Depends, Request, status

from com.qode.qrew.v1.identity.core.dependencies import get_admin_user
from com.qode.qrew.v1.identity.core.dependencies import limiter
from com.qode.qrew.v1.identity.models.user import User
from com.qode.qrew.v1.identity.schemas.admin import FingerprintAdminResponse
from com.qode.qrew.v1.identity.services.application.authentication.device.fingerprint import (
    FingerprintService,
)

from ._deps import get_fingerprint_service

router = APIRouter(prefix="/fingerprints")


@router.get(
    "/{fingerprint_hash}",
    response_model=FingerprintAdminResponse,
    status_code=status.HTTP_200_OK,
    summary="List accounts associated with a device fingerprint",
)
@limiter.limit("60/minute")  # type: ignore[misc]
async def get_fingerprint(
    request: Request,
    fingerprint_hash: str,
    _admin: User = Depends(get_admin_user),
    service: FingerprintService = Depends(get_fingerprint_service),
) -> FingerprintAdminResponse:
    """List accounts associated with a device fingerprint."""
    user_ids = await service.get_by_hash(fingerprint_hash)
    return FingerprintAdminResponse(
        fingerprint_hash=fingerprint_hash,
        user_ids=[str(uid) for uid in user_ids],
        account_count=len(user_ids),
    )
