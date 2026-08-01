import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status

from com.qode.qrew.v1.identity.core.dependencies import (
    get_current_user,
    get_totp_service,
    get_totp_user,
    limiter,
)
from com.qode.qrew.v1.identity.models.user import User
from com.qode.qrew.v1.identity.repositories.session import SessionRepository
from com.qode.qrew.v1.identity.repositories.device import DeviceRepository
from com.qode.qrew.v1.identity.schemas.authentication.totp import (
    TotpConfirmRequest,
    TotpConfirmResponse,
    TotpDisableRequest,
    TotpDisableResponse,
    TotpSetupResponse,
    TotpStatusResponse,
    TotpVerifyRequest,
    TotpVerifyResponse,
)
from com.qode.qrew.v1.identity.services.application.authentication.login.guards.totp import (
    TotpError,
    TotpService,
)
from com.qode.qrew.v1.identity.core.database import get_db
from com.qode.qrew.v1.identity.core.config import settings
from com.qode.qrew.v1.identity.services.application.authentication.token.security import (
    create_access_token,
    create_refresh_token,
    extract_jti,
)
from com.qode.qrew.v1.identity.models.session import Session
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis
from com.qode.qrew.v1.identity.core.dependencies import get_redis

router = APIRouter(prefix="/totp", tags=["totp"])


def _totp_error(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={"message": message, "field": "code"},
    )


@router.get(
    "/status",
    response_model=TotpStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Check whether 2FA is enabled for the current user",
)
async def totp_status(
    current_user: User = Depends(get_current_user),
) -> TotpStatusResponse:
    return TotpStatusResponse(enabled=current_user.totp_enabled)


@router.post(
    "/setup",
    response_model=TotpSetupResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate a new TOTP secret and provisioning URI",
)
@limiter.limit("10/minute")  # type: ignore[misc]
async def totp_setup(
    request: Request,
    current_user: User = Depends(get_current_user),
    service: TotpService = Depends(get_totp_service),
) -> TotpSetupResponse:
    del request
    secret, uri, backup_codes = service.generate_setup(current_user)
    return TotpSetupResponse(provisioning_uri=uri, backup_codes=backup_codes, secret=secret)


@router.post(
    "/confirm",
    response_model=TotpConfirmResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify first TOTP code and enable 2FA",
)
@limiter.limit("10/minute")  # type: ignore[misc]
async def totp_confirm(
    request: Request,
    body: TotpConfirmRequest,
    current_user: User = Depends(get_current_user),
    service: TotpService = Depends(get_totp_service),
) -> TotpConfirmResponse:
    del request
    try:
        await service.confirm(current_user, body.secret, body.code, body.backup_codes)
    except TotpError as exc:
        raise _totp_error(exc.message) from exc
    return TotpConfirmResponse(message="Two-factor authentication enabled.")


@router.post(
    "/verify",
    response_model=TotpVerifyResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify TOTP code after login challenge and issue full session tokens",
)
@limiter.limit("10/minute")  # type: ignore[misc]
async def totp_verify(
    request: Request,
    body: TotpVerifyRequest,
    totp_user: User = Depends(get_totp_user),
    service: TotpService = Depends(get_totp_service),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),  # type: ignore[type-arg]
) -> TotpVerifyResponse:
    del request
    try:
        await service.verify_login(totp_user, body.code)
    except TotpError as exc:
        raise _totp_error(exc.message) from exc

    ip = None
    device_id: uuid.UUID | None = None

    refresh_token = create_refresh_token(str(totp_user.id))
    jti = extract_jti(refresh_token)
    access_token = create_access_token(str(totp_user.id), session_jti=jti, is_admin=totp_user.is_admin)

    if jti:
        session_repo = SessionRepository(db)
        await session_repo.create(
            Session(
                id=uuid.uuid4(),
                user_id=totp_user.id,
                jti=jti,
                ip_address=ip,
                user_agent=None,
                device_fingerprint=None,
                device_id=device_id,
            )
        )

    return TotpVerifyResponse(access_token=access_token, refresh_token=refresh_token)


@router.delete(
    "/disable",
    response_model=TotpDisableResponse,
    status_code=status.HTTP_200_OK,
    summary="Disable 2FA after verifying current TOTP code",
)
@limiter.limit("10/minute")  # type: ignore[misc]
async def totp_disable(
    request: Request,
    body: TotpDisableRequest,
    current_user: User = Depends(get_current_user),
    service: TotpService = Depends(get_totp_service),
) -> TotpDisableResponse:
    del request
    try:
        await service.disable(current_user, body.code)
    except TotpError as exc:
        raise _totp_error(exc.message) from exc
    return TotpDisableResponse(message="Two-factor authentication disabled.")
