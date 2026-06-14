import contextlib
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status

from com.qode.qrew.v1.identity.services.infra.limiter import limiter
from com.qode.qrew.v1.identity.services.ratelimit import rate_limit
from com.qode.qrew.v1.identity.services.ratelimit.dependencies import (
    audit_on_rejection,
    limiter_for,
)
from com.qode.qrew.v1.identity.schemas.auth.auth import (
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    LogoutResponse,
    RefreshRequest,
    RefreshResponse,
)
from com.qode.qrew.v1.identity.services.auth.login import LoginError, LoginService
from com.qode.qrew.v1.identity.services.auth.login_lockout import LoginLockoutError
from com.qode.qrew.v1.identity.services.auth.logout import LogoutError, LogoutService
from com.qode.qrew.v1.identity.services.auth.refresh import (
    RefreshError,
    RefreshService,
    decode_signature_header,
)

from ._deps import (
    domain_error,
    get_login_service,
    get_logout_service,
    get_refresh_service,
)

router = APIRouter()


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Log in as a registered user",
)
@limiter.limit("10/minute")  # type: ignore[misc]
@rate_limit(
    [("ip", 10, 60)],
    limiter_factory=limiter_for,
    on_rejection=audit_on_rejection,
)
async def login(
    request: Request,
    body: LoginRequest,
    service: LoginService = Depends(get_login_service),
) -> LoginResponse:
    """Log in as a registered user."""
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    device_fingerprint = request.headers.get("X-Device-Fingerprint")
    device_id: uuid.UUID | None = None
    device_id_header = request.headers.get("X-Device-Id")
    if device_id_header:
        with contextlib.suppress(ValueError):
            device_id = uuid.UUID(device_id_header)
    try:
        return await service.login(body, ip_address, user_agent, device_fingerprint, device_id)
    except LoginLockoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"message": "Invalid email or password", "field": None},
            headers={"Retry-After": str(exc.retry_after_seconds)},
        ) from exc
    except LoginError as exc:
        raise domain_error(exc.message, exc.field, status.HTTP_401_UNAUTHORIZED) from exc


@router.post(
    "/refresh",
    response_model=RefreshResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh an access token using a valid refresh token",
)
@limiter.limit("20/minute")  # type: ignore[misc]
async def refresh(
    request: Request,
    body: RefreshRequest,
    service: RefreshService = Depends(get_refresh_service),
) -> RefreshResponse:
    """Refresh an access token."""
    signature = decode_signature_header(request.headers.get("X-Device-Signature"))
    try:
        return await service.refresh(body, signature)
    except RefreshError as exc:
        raise domain_error(exc.message, exc.field, status.HTTP_401_UNAUTHORIZED) from exc


@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Log out and invalidate the refresh token",
)
@limiter.limit("20/minute")  # type: ignore[misc]
async def logout(
    request: Request,
    body: LogoutRequest,
    service: LogoutService = Depends(get_logout_service),
) -> LogoutResponse:
    """Log out and invalidate the refresh token."""
    try:
        await service.logout(body.refresh_token)
        return LogoutResponse(message="Logged out successfully.")
    except LogoutError as exc:
        raise domain_error(exc.message, exc.field, status.HTTP_401_UNAUTHORIZED) from exc
