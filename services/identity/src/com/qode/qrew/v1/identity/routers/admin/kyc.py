import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status

from com.qode.qrew.v1.identity.core.dependencies import get_admin_user
from com.qode.qrew.v1.identity.core.dependencies import limiter
from com.qode.qrew.v1.identity.models.user import User
from com.qode.qrew.v1.identity.schemas.admin import (
    KycReviewRequest,
    KycReviewResponse,
)
from com.qode.qrew.v1.identity.services.application.authentication.kyc.review import (
    KycReviewError,
    KycReviewService,
)

from ._deps import get_kyc_review_service

router = APIRouter(prefix="/kyc")


@router.post(
    "/{user_id}/review",
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
    """Approve or reject a pending KYC submission."""
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
