# exposes the endpoints that recover an account with a national identity document
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status

from com.qode.qrew.v1.identity.core.dependencies import get_recovery_user
from com.qode.qrew.v1.identity.core.dependencies import limiter
from com.qode.qrew.v1.identity.models.user import User
from com.qode.qrew.v1.identity.schemas.account import (
    RecoveryBeginResponse,
    RecoveryCompleteResponse,
)
from com.qode.qrew.v1.identity.schemas.passkey import (
    PasskeyRegistrationCompleteRequest,
)
from com.qode.qrew.v1.identity.services.application.authentication.account.recovery import (
    RecoveryError,
    RecoveryService,
)

from ._deps import domain_error, get_recovery_service

router = APIRouter(prefix="/recovery")

_MAX_FILE_BYTES = 10 * 1024 * 1024
_ALLOWED_MAGIC = [
    b"\xff\xd8\xff",
    b"\x89PNG\r\n\x1a\n",
    b"%PDF-",
]


# checks that an uploaded file matches an accepted document type
def _is_allowed_file(content: bytes) -> bool:
    return any(content.startswith(magic) for magic in _ALLOWED_MAGIC)


# verifies a national identity document and starts account recovery
@router.post(
    "/begin",
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
    content = await document.read()
    if len(content) > _MAX_FILE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large"
        )
    if not _is_allowed_file(content):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Unsupported file type"
        )
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


# completes account recovery by registering a new passkey
@router.post(
    "/complete",
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
    try:
        await service.complete(current_user, body)
        return RecoveryCompleteResponse(message="Account recovery complete.")
    except RecoveryError as exc:
        raise domain_error(exc.message, exc.field, status.HTTP_400_BAD_REQUEST) from exc
