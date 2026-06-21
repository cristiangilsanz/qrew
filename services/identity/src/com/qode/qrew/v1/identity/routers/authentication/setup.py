from typing import Annotated

from fastapi import APIRouter, Depends, File, Request, UploadFile, status

from com.qode.qrew.v1.identity.core.dependencies import get_setup_or_full_user
from com.qode.qrew.v1.identity.core.dependencies import limiter
from com.qode.qrew.v1.identity.models.user import User
from com.qode.qrew.v1.identity.schemas.authentication.auth import LoginResponse
from com.qode.qrew.v1.identity.schemas.kyc import KycUploadResponse
from com.qode.qrew.v1.identity.services.application.authentication.kyc.submission import (
    KycError,
    KycService,
)
from com.qode.qrew.v1.identity.services.application.authentication.registration.setup import (
    CompleteSetupService,
    SetupError,
)

from ._deps import (
    domain_error,
    get_complete_setup_service,
    get_kyc_service,
)

router = APIRouter(prefix="/setup")


@router.post(
    "/kyc/upload",
    response_model=KycUploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit a national ID document for KYC verification",
)
@limiter.limit("3/hour")  # type: ignore[misc]
async def kyc_upload(
    request: Request,
    document: Annotated[UploadFile, File()],
    current_user: User = Depends(get_setup_or_full_user),
    service: KycService = Depends(get_kyc_service),
) -> KycUploadResponse:
    """Submit a national ID document for KYC verification."""
    content = await document.read()
    try:
        final_status = await service.upload(current_user, content)
        return KycUploadResponse(
            message="KYC document submitted for review.",
            kyc_status=final_status,
        )
    except KycError as exc:
        raise domain_error(exc.message, exc.field, status.HTTP_400_BAD_REQUEST) from exc


@router.post(
    "/complete-setup",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Exchange a setup token for a full access token",
)
@limiter.limit("10/hour")  # type: ignore[misc]
async def complete_setup(
    request: Request,
    current_user: User = Depends(get_setup_or_full_user),
    service: CompleteSetupService = Depends(get_complete_setup_service),
) -> LoginResponse:
    """Exchange a setup token for a full access token."""
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    device_fingerprint = request.headers.get("X-Device-Fingerprint")
    try:
        return await service.complete(current_user, ip_address, user_agent, device_fingerprint)
    except SetupError as exc:
        raise domain_error(exc.message, exc.field, status.HTTP_400_BAD_REQUEST) from exc
