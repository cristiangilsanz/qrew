# exposes the endpoints that register authenticate reassert and manage passkeys
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from pagination import Page
from middleware import client_ip

from com.qode.qrew.v1.identity.core.config import settings
from com.qode.qrew.v1.identity.core.dependencies import (
    get_current_session,
    get_current_user,
    get_setup_or_full_user,
)
from com.qode.qrew.v1.identity.core.dependencies import limiter
from com.qode.qrew.v1.identity.models.session import Session
from com.qode.qrew.v1.identity.models.user import User
from com.qode.qrew.v1.identity.schemas.authentication.auth import LoginResponse
from com.qode.qrew.v1.identity.schemas.passkey import (
    PasskeyAssertBeginResponse,
    PasskeyAssertCompleteResponse,
    PasskeyAuthenticationBeginRequest,
    PasskeyAuthenticationCompleteRequest,
    PasskeyRegistrationCompleteRequest,
    PasskeyRegistrationCompleteResponse,
    PasskeyRenameRequest,
    PasskeyResponse,
)
from com.qode.qrew.v1.identity.services.application.authentication.passkey import (
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

router = APIRouter(prefix="/passkeys")


# an account holds exactly one passkey, so a second attempt is a conflict
def _registration_error(exc: PasskeyError) -> HTTPException:
    http_status = (
        status.HTTP_409_CONFLICT
        if "already registered" in exc.message
        else status.HTTP_400_BAD_REQUEST
    )
    return domain_error(exc.message, exc.field, http_status)


# starts registering a new passkey for the caller
@router.post(
    "/register/begin",
    status_code=status.HTTP_200_OK,
    summary="Begin passkey registration",
)
@limiter.limit("10/hour")  # type: ignore[misc]
async def passkey_register_begin(
    request: Request,
    current_user: User = Depends(get_setup_or_full_user),
    service: PasskeyRegistrationService = Depends(get_passkey_registration_service),
) -> Response:
    try:
        options_json = await service.begin(current_user)
    except PasskeyError as exc:
        raise _registration_error(exc) from exc
    return Response(content=options_json, media_type="application/json")


# completes registering a new passkey for the caller
@router.post(
    "/register/complete",
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
    try:
        await service.complete(current_user, body)
        return PasskeyRegistrationCompleteResponse(message="Passkey registered successfully.")
    except PasskeyError as exc:
        raise _registration_error(exc) from exc


# starts signing in with a passkey
@router.post(
    "/authenticate/begin",
    status_code=status.HTTP_200_OK,
    summary="Begin passkey authentication",
)
@limiter.limit("10/minute")  # type: ignore[misc]
async def passkey_authenticate_begin(
    request: Request,
    body: PasskeyAuthenticationBeginRequest,
    service: PasskeyAuthenticationService = Depends(get_passkey_authentication_service),
) -> Response:
    try:
        options_json = await service.begin(body.email)
        return Response(content=options_json, media_type="application/json")
    except PasskeyError as exc:
        raise domain_error(exc.message, exc.field, status.HTTP_400_BAD_REQUEST) from exc


# completes signing in with a passkey
@router.post(
    "/authenticate/complete",
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
    ip_address = client_ip(request, settings.trusted_proxy_ip)
    user_agent = request.headers.get("User-Agent")
    device_fingerprint = request.headers.get("X-Device-Fingerprint")
    try:
        return await service.complete(body, ip_address, user_agent, device_fingerprint)
    except PasskeyError as exc:
        raise domain_error(exc.message, exc.field, status.HTTP_400_BAD_REQUEST) from exc


# starts reasserting a passkey for the current session
@router.post(
    "/assert/begin",
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
    try:
        options = await service.begin(current_user, current_session.jti)
        return PasskeyAssertBeginResponse(options=options)
    except PasskeyError as exc:
        raise domain_error(exc.message, exc.field, status.HTTP_400_BAD_REQUEST) from exc


# completes a passkey reassertion and stamps the session
@router.post(
    "/assert/complete",
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
    try:
        asserted_at, access_token = await service.complete(current_user, current_session, body)
        return PasskeyAssertCompleteResponse(asserted_at=asserted_at, access_token=access_token)
    except PasskeyError as exc:
        raise domain_error(exc.message, exc.field, status.HTTP_400_BAD_REQUEST) from exc


# lists the caller's passkeys
@router.get(
    "/",
    response_model=Page[PasskeyResponse],
    status_code=status.HTTP_200_OK,
    summary="List all passkeys for the current user",
)
@limiter.limit("30/minute")  # type: ignore[misc]
async def list_passkeys(
    request: Request,
    current_user: User = Depends(get_current_user),
    service: PasskeyManagementService = Depends(get_passkey_management_service),
) -> Page[PasskeyResponse]:
    listing = await service.list_passkeys(current_user.id)
    return Page[PasskeyResponse](items=listing.passkeys, next_cursor=None)


# deletes one of the caller's passkeys
@router.delete(
    "/{passkey_id}",
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
    try:
        pk_id = uuid.UUID(passkey_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Passkey rejected.", "field": "passkey_id"},
        ) from exc
    try:
        await service.delete_passkey(pk_id, current_user.id)
    except PasskeyError as exc:
        http_status = (
            status.HTTP_409_CONFLICT if "last passkey" in exc.message else status.HTTP_404_NOT_FOUND
        )
        raise domain_error(exc.message, exc.field, http_status) from exc


# renames one of the caller's passkeys
@router.patch(
    "/{passkey_id}",
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
    try:
        pk_id = uuid.UUID(passkey_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Passkey rejected.", "field": "passkey_id"},
        ) from exc
    try:
        return await service.rename_passkey(pk_id, current_user.id, body.name)
    except PasskeyError as exc:
        raise domain_error(exc.message, exc.field, status.HTTP_404_NOT_FOUND) from exc
