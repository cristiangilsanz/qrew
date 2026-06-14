from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, status

from com.qode.qrew.v1.identity.services.auth.auth import get_recovery_user
from com.qode.qrew.v1.identity.services.infra.limiter import limiter
from com.qode.qrew.v1.identity.models.auth.user import User
from com.qode.qrew.v1.identity.schemas.account.account import (
    RecoveryBeginResponse,
    RecoveryCompleteResponse,
)
from com.qode.qrew.v1.identity.schemas.passkey.passkey import (
    PasskeyRegistrationCompleteRequest,
)
from com.qode.qrew.v1.identity.services.account.recovery import (
    RecoveryError,
    RecoveryService,
)

from ._deps import domain_error, get_recovery_service

router = APIRouter()


@router.post(
    "/recovery/begin",
    response_model=RecoveryBeginResponse,
    status_code=status.HTTP_200_OK,
    summary="Begin account recovery with national ID document",
)
@limiter.limit("5/hour")  # type: ignore[misc]
async def recovery_begin(
    request: Request,
    email: Annotated[str, Form()],
    document: Annotated[UploadFile, File()],
    service: RecoveryService = Depends(get_recovery_service),
) -> RecoveryBeginResponse:
    """Begin account recovery."""
    content = await document.read()
    recovery_token, passkey_options = await service.begin(email, content)
    if recovery_token is None:
        return RecoveryBeginResponse(
            message=("If a matching account was found, recovery instructions have been sent.")
        )
    return RecoveryBeginResponse(
        message="Identity verified. Complete recovery by registering a new passkey.",
        recovery_token=recovery_token,
        passkey_options=passkey_options,
    )


@router.post(
    "/recovery/complete",
    response_model=RecoveryCompleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Complete account recovery by registering a new passkey",
)
@limiter.limit("5/hour")  # type: ignore[misc]
async def recovery_complete(
    request: Request,
    body: PasskeyRegistrationCompleteRequest,
    current_user: User = Depends(get_recovery_user),
    service: RecoveryService = Depends(get_recovery_service),
) -> RecoveryCompleteResponse:
    """Complete account recovery."""
    try:
        await service.complete(current_user, body)
        return RecoveryCompleteResponse(message="Account recovery complete.")
    except RecoveryError as exc:
        raise domain_error(exc.message, exc.field, status.HTTP_400_BAD_REQUEST) from exc
