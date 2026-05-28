import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from com.qode.qrew.v1.service.core.auth.auth import (
    get_current_session,
    get_current_user,
    get_setup_or_full_user,
)
from com.qode.qrew.v1.service.core.infra.limiter import limiter
from com.qode.qrew.v1.service.models.auth.session import Session
from com.qode.qrew.v1.service.models.auth.user import User
from com.qode.qrew.v1.service.schemas.auth.auth import LoginResponse
from com.qode.qrew.v1.service.schemas.passkey.passkey import (
    PasskeyAssertBeginResponse,
    PasskeyAssertCompleteResponse,
    PasskeyAuthenticationBeginRequest,
    PasskeyAuthenticationCompleteRequest,
    PasskeyListResponse,
    PasskeyRegistrationCompleteRequest,
    PasskeyRegistrationCompleteResponse,
    PasskeyRenameRequest,
    PasskeyResponse,
)
from com.qode.qrew.v1.service.services.passkey import (
    PasskeyAuthenticationService,
    PasskeyError,
    PasskeyManagementService,
    PasskeyReassertionService,
    PasskeyRegistrationService,
)

from ._deps import (
    domain_error,
    get_passkey_authentication_service,
    get_passkey_management_service,
    get_passkey_reassertion_service,
    get_passkey_registration_service,
)

router = APIRouter()


@router.post(
    "/passkey/register/begin",
    status_code=status.HTTP_200_OK,
    summary="Begin passkey registration",
)
@limiter.limit("10/hour")  # type: ignore[misc]
async def passkey_register_begin(
    request: Request,
    current_user: User = Depends(get_setup_or_full_user),
    service: PasskeyRegistrationService = Depends(get_passkey_registration_service),
) -> Response:
    """Generate passkey registration options for the current user."""
    options_json = await service.begin(current_user)
    return Response(content=options_json, media_type="application/json")


@router.post(
    "/passkey/register/complete",
    response_model=PasskeyRegistrationCompleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Complete passkey registration",
)
@limiter.limit("10/hour")  # type: ignore[misc]
async def passkey_register_complete(
    request: Request,
    body: PasskeyRegistrationCompleteRequest,
    current_user: User = Depends(get_setup_or_full_user),
    service: PasskeyRegistrationService = Depends(get_passkey_registration_service),
) -> PasskeyRegistrationCompleteResponse:
    """Complete passkey registration."""
    try:
        await service.complete(current_user, body)
        return PasskeyRegistrationCompleteResponse(
            message="Passkey registered successfully."
        )
    except PasskeyError as exc:
        raise domain_error(exc.message, exc.field, status.HTTP_400_BAD_REQUEST) from exc


@router.post(
    "/passkey/authenticate/begin",
    status_code=status.HTTP_200_OK,
    summary="Begin passkey authentication",
)
@limiter.limit("10/minute")  # type: ignore[misc]
async def passkey_authenticate_begin(
    request: Request,
    body: PasskeyAuthenticationBeginRequest,
    service: PasskeyAuthenticationService = Depends(get_passkey_authentication_service),
) -> Response:
    """Generate passkey assertion options for an email address."""
    try:
        options_json = await service.begin(body.email)
        return Response(content=options_json, media_type="application/json")
    except PasskeyError as exc:
        raise domain_error(exc.message, exc.field, status.HTTP_400_BAD_REQUEST) from exc


@router.post(
    "/passkey/authenticate/complete",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Complete passkey authentication",
)
@limiter.limit("10/minute")  # type: ignore[misc]
async def passkey_authenticate_complete(
    request: Request,
    body: PasskeyAuthenticationCompleteRequest,
    service: PasskeyAuthenticationService = Depends(get_passkey_authentication_service),
) -> LoginResponse:
    """Complete passkey authentication and return access tokens."""
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    device_fingerprint = request.headers.get("X-Device-Fingerprint")
    try:
        return await service.complete(body, ip_address, user_agent, device_fingerprint)
    except PasskeyError as exc:
        raise domain_error(exc.message, exc.field, status.HTTP_400_BAD_REQUEST) from exc


@router.post(
    "/passkey/assert/begin",
    response_model=PasskeyAssertBeginResponse,
    status_code=status.HTTP_200_OK,
    summary="Begin a passkey re-assertion for the current session",
)
@limiter.limit("30/minute")  # type: ignore[misc]
async def passkey_assert_begin(
    request: Request,
    current_user: User = Depends(get_current_user),
    current_session: Session = Depends(get_current_session),
    service: PasskeyReassertionService = Depends(get_passkey_reassertion_service),
) -> PasskeyAssertBeginResponse:
    """Begin a passkey re-assertion for the current session."""
    try:
        options = await service.begin(current_user, current_session.jti)
        return PasskeyAssertBeginResponse(options=options)
    except PasskeyError as exc:
        raise domain_error(exc.message, exc.field, status.HTTP_400_BAD_REQUEST) from exc


@router.post(
    "/passkey/assert/complete",
    response_model=PasskeyAssertCompleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Complete a passkey re-assertion and stamp the session",
)
@limiter.limit("30/minute")  # type: ignore[misc]
async def passkey_assert_complete(
    request: Request,
    body: PasskeyAuthenticationCompleteRequest,
    current_user: User = Depends(get_current_user),
    current_session: Session = Depends(get_current_session),
    service: PasskeyReassertionService = Depends(get_passkey_reassertion_service),
) -> PasskeyAssertCompleteResponse:
    """Complete a passkey re-assertion and stamp the session."""
    try:
        asserted_at = await service.complete(current_user, current_session, body)
        return PasskeyAssertCompleteResponse(asserted_at=asserted_at)
    except PasskeyError as exc:
        raise domain_error(exc.message, exc.field, status.HTTP_400_BAD_REQUEST) from exc


@router.get(
    "/passkeys",
    response_model=PasskeyListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all passkeys for the current user",
)
@limiter.limit("30/minute")  # type: ignore[misc]
async def list_passkeys(
    request: Request,
    current_user: User = Depends(get_current_user),
    service: PasskeyManagementService = Depends(get_passkey_management_service),
) -> PasskeyListResponse:
    """List all passkeys for the current user."""
    return await service.list_passkeys(current_user.id)


@router.delete(
    "/passkeys/{passkey_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a passkey by id",
)
@limiter.limit("20/minute")  # type: ignore[misc]
async def delete_passkey(
    request: Request,
    passkey_id: str,
    current_user: User = Depends(get_current_user),
    service: PasskeyManagementService = Depends(get_passkey_management_service),
) -> None:
    """Remove a passkey if it is not the user's last one."""
    try:
        pk_id = uuid.UUID(passkey_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Invalid passkey ID", "field": "passkey_id"},
        ) from exc
    try:
        await service.delete_passkey(pk_id, current_user.id)
    except PasskeyError as exc:
        http_status = (
            status.HTTP_409_CONFLICT
            if "last passkey" in exc.message
            else status.HTTP_404_NOT_FOUND
        )
        raise domain_error(exc.message, exc.field, http_status) from exc


@router.patch(
    "/passkeys/{passkey_id}",
    response_model=PasskeyResponse,
    status_code=status.HTTP_200_OK,
    summary="Rename a passkey",
)
@limiter.limit("20/minute")  # type: ignore[misc]
async def rename_passkey(
    request: Request,
    passkey_id: str,
    body: PasskeyRenameRequest,
    current_user: User = Depends(get_current_user),
    service: PasskeyManagementService = Depends(get_passkey_management_service),
) -> PasskeyResponse:
    """Rename a passkey."""
    try:
        pk_id = uuid.UUID(passkey_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Invalid passkey ID", "field": "passkey_id"},
        ) from exc
    try:
        return await service.rename_passkey(pk_id, current_user.id, body.name)
    except PasskeyError as exc:
        raise domain_error(exc.message, exc.field, status.HTTP_404_NOT_FOUND) from exc
