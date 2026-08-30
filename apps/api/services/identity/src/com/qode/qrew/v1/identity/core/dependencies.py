# provides the shared fastapi dependencies for the identity service
import uuid
from collections.abc import AsyncGenerator
from typing import Annotated, Optional

import redis.asyncio as aioredis
import structlog
from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from security import matches_internal_key
from jwt import ExpiredSignatureError, InvalidTokenError
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.identity.core.config import settings
from com.qode.qrew.v1.identity.core.database import get_db
from com.qode.qrew.v1.identity.core.utils.geoip import GeoIpService
from com.qode.qrew.v1.identity.models.session import Session
from com.qode.qrew.v1.identity.models.user import User
from com.qode.qrew.v1.identity.repositories.device import DeviceRepository
from com.qode.qrew.v1.identity.repositories.fingerprint import DeviceFingerprintRepository
from com.qode.qrew.v1.identity.repositories.passkey import PasskeyCredentialRepository
from com.qode.qrew.v1.identity.repositories.session import SessionRepository
from com.qode.qrew.v1.identity.repositories.user import UserRepository
from com.qode.qrew.v1.identity.services.application.audit import AuditService
from com.qode.qrew.v1.identity.core.utils import jwt as jwt_keys
from com.qode.qrew.v1.identity.services.application.authentication.login.guards.breach_check import (
    PasswordBreachChecker,
)
from com.qode.qrew.v1.identity.services.application.authentication.login.flow.login import (
    LoginService,
)
from com.qode.qrew.v1.identity.services.application.authentication.login.guards.anomaly import (
    LoginAnomalyService,
)
from com.qode.qrew.v1.identity.services.application.authentication.login.guards.lockout import (
    LoginLockoutService,
)
from com.qode.qrew.v1.identity.services.application.authentication.login.flow.logout import (
    LogoutService,
)
from com.qode.qrew.v1.identity.services.application.authentication.profile import ProfileService
from com.qode.qrew.v1.identity.services.application.authentication.token.refresh import (
    RefreshService,
)
from com.qode.qrew.v1.identity.services.application.authentication.login.guards.session_cap import (
    SessionCapEnforcer,
)
from com.qode.qrew.v1.identity.services.application.authentication.account.deletion import (
    AccountDeletionService,
)
from com.qode.qrew.v1.identity.services.application.authentication.account.changes.email_change import (
    EmailChangeService,
)
from com.qode.qrew.v1.identity.services.application.authentication.account.changes.password_change import (
    PasswordChangeService,
)
from com.qode.qrew.v1.identity.services.application.authentication.account.changes.phone_change import (
    PhoneChangeService,
)
from com.qode.qrew.v1.identity.services.application.authentication.account.changes.forgot_password import (
    ForgotPasswordService,
)
from com.qode.qrew.v1.identity.services.application.authentication.account.recovery import (
    RecoveryService,
)
from com.qode.qrew.v1.identity.services.application.authentication.device.attestation.verifier import (
    build_attestation_verifier,
)
from com.qode.qrew.v1.identity.services.application.authentication.device.management import (
    DeviceService,
)
from com.qode.qrew.v1.identity.services.application.authentication.device.attestation.attestor import (
    DeviceAttestationService,
)
from com.qode.qrew.v1.identity.services.application.authentication.device.binding import (
    DeviceBindingService,
)
from com.qode.qrew.v1.identity.services.application.authentication.device.fingerprint import (
    FingerprintService,
)
from com.qode.qrew.v1.identity.services.application.authentication.kyc.submission import KycService
from com.qode.qrew.v1.identity.services.application.authentication.kyc.review import (
    KycReviewService,
)
from com.qode.qrew.v1.identity.services.application.authentication.kyc.ocr import OcrService
from com.qode.qrew.v1.identity.services.application.notification.dispatcher import (
    NotificationDispatcher,
    build_notification_dispatcher,
)
from com.qode.qrew.v1.identity.services.application.authentication.passkey import (
    PasskeyAuthenticationService,
    PasskeyManagementService,
    PasskeyReassertionService,
    PasskeyRegistrationService,
)
from com.qode.qrew.v1.identity.services.application.authentication.registration.captcha import (
    CaptchaService,
    build_captcha_service,
)
from com.qode.qrew.v1.identity.services.application.authentication.registration.setup import (
    CompleteSetupService,
)
from com.qode.qrew.v1.identity.services.application.authentication.registration.signup import (
    RegistrationService,
)
from com.qode.qrew.v1.identity.services.application.authentication.registration.verification.resender import (
    ResendEmailVerificationService,
    ResendPhoneOtpService,
)
from com.qode.qrew.v1.identity.services.application.authentication.registration.verification.verifier import (
    EmailVerificationService,
    PhoneVerificationService,
)
from com.qode.qrew.v1.identity.services.application.authentication.session import SessionService
from com.qode.qrew.v1.identity.services.application.authentication.login.guards.totp import (
    TotpService,
)

logger = structlog.get_logger(__name__)

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    enabled=settings.ratelimit_enabled,
)
limiter.enabled = settings.ratelimit_enabled


# rejects a request without a valid internal api key
def verify_internal_key(x_internal_key: str = Header(alias="X-Internal-Key")) -> None:
    if not matches_internal_key(x_internal_key, settings.internal_api_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


_bearer = HTTPBearer(auto_error=False)

_CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail={"message": "Token expired.", "field": None},
)

_SETUP_REQUIRED_EXCEPTION = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail={
        "message": "Setup not complete.",
        "field": None,
    },
)


# yields a redis client for the duration of a request
async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:  # type: ignore[type-arg]
    client: aioredis.Redis = aioredis.from_url(  # type: ignore[type-arg]
        settings.redis_url, decode_responses=False
    )
    try:
        yield client
    finally:
        await client.aclose()


# resolves the user a token or trusted header identifies
async def _resolve_user(
    credentials: Optional[HTTPAuthorizationCredentials],
    db: AsyncSession,
    *,
    allow_setup: bool,
    trusted_user_id: Optional[uuid.UUID] = None,
) -> User:
    if trusted_user_id is not None:
        user = await UserRepository(db).get_by_id(trusted_user_id)
        if user is None or not user.is_active:
            raise _CREDENTIALS_EXCEPTION
        return user

    if credentials is None:
        raise _CREDENTIALS_EXCEPTION

    try:
        matched, payload = jwt_keys.verify_any(
            (jwt_keys.ACCESS, jwt_keys.SETUP), credentials.credentials
        )
    except (ExpiredSignatureError, InvalidTokenError) as exc:
        raise _CREDENTIALS_EXCEPTION from exc

    if payload.get("type") != "access":
        raise _CREDENTIALS_EXCEPTION

    if matched == jwt_keys.SETUP and not allow_setup:
        raise _SETUP_REQUIRED_EXCEPTION

    subject = payload.get("sub")
    if not isinstance(subject, str):
        raise _CREDENTIALS_EXCEPTION

    try:
        user_id = uuid.UUID(subject)
    except ValueError as exc:
        raise _CREDENTIALS_EXCEPTION from exc

    user = await UserRepository(db).get_by_id(user_id)
    if user is None or not user.is_active:
        raise _CREDENTIALS_EXCEPTION

    return user


# resolves the authenticated user requiring a fully set up account
async def get_current_user(
    request: Request,
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(_bearer)] = None,
    db: AsyncSession = Depends(get_db),
) -> User:
    user_id_str = request.headers.get("x-authenticated-user-id")
    trusted_id: Optional[uuid.UUID] = None
    if user_id_str:
        try:
            trusted_id = uuid.UUID(user_id_str)
        except ValueError as exc:
            raise _CREDENTIALS_EXCEPTION from exc
    return await _resolve_user(credentials, db, allow_setup=False, trusted_user_id=trusted_id)


# resolves the authenticated user allowing an account still in setup
async def get_setup_or_full_user(
    request: Request,
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(_bearer)] = None,
    db: AsyncSession = Depends(get_db),
) -> User:
    user_id_str = request.headers.get("x-authenticated-user-id")
    trusted_id: Optional[uuid.UUID] = None
    if user_id_str:
        try:
            trusted_id = uuid.UUID(user_id_str)
        except ValueError as exc:
            raise _CREDENTIALS_EXCEPTION from exc
    return await _resolve_user(credentials, db, allow_setup=True, trusted_user_id=trusted_id)


# resolves the user a recovery token identifies
async def get_recovery_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = jwt_keys.verify(jwt_keys.RECOVERY, credentials.credentials)
    except (ExpiredSignatureError, InvalidTokenError) as exc:
        raise _CREDENTIALS_EXCEPTION from exc

    if payload.get("type") != "access" or payload.get("scope") != "recovery":
        raise _CREDENTIALS_EXCEPTION

    subject = payload.get("sub")
    if not isinstance(subject, str):
        raise _CREDENTIALS_EXCEPTION

    try:
        user_id = uuid.UUID(subject)
    except ValueError as exc:
        raise _CREDENTIALS_EXCEPTION from exc

    user = await UserRepository(db).get_by_id(user_id)
    if user is None or not user.is_active:
        raise _CREDENTIALS_EXCEPTION

    return user


# resolves the caller's session from an access token
async def get_current_session(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    db: AsyncSession = Depends(get_db),
    redis: Annotated[aioredis.Redis, Depends(get_redis)] = ...,  # type: ignore[type-arg, assignment]
) -> Session:
    try:
        payload = jwt_keys.verify(jwt_keys.ACCESS, credentials.credentials)
    except (ExpiredSignatureError, InvalidTokenError) as exc:
        raise _CREDENTIALS_EXCEPTION from exc

    if payload.get("type") != "access" or payload.get("scope") != "access":
        raise _CREDENTIALS_EXCEPTION

    jti = payload.get("jti")
    if not isinstance(jti, str):
        raise _CREDENTIALS_EXCEPTION

    if await redis.get(f"blacklist:jti:{jti}") is not None:
        raise _CREDENTIALS_EXCEPTION

    session = await SessionRepository(db).get_by_jti(jti)
    if session is None:
        raise _CREDENTIALS_EXCEPTION

    return session


# rejects a request whose authenticated user is not an admin
async def get_admin_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": "Admin access required.", "field": None},
        )
    return current_user


# converts a domain message and field into an http exception
def domain_error(message: str, field: str | None, http_status: int) -> HTTPException:
    return HTTPException(status_code=http_status, detail={"message": message, "field": field})


# builds the captcha service
def get_captcha_service() -> CaptchaService:
    return build_captcha_service()


# builds the notification dispatcher
def get_notification_service() -> NotificationDispatcher:
    return build_notification_dispatcher()


# builds the geoip service
def get_geoip_service() -> GeoIpService:
    return GeoIpService(settings.geoip_db_path)


# builds the ocr service
def get_ocr_service() -> OcrService:
    return OcrService()


# builds a login service for a request
def get_login_service(
    db: AsyncSession = Depends(get_db),
    redis: Annotated[aioredis.Redis, Depends(get_redis)] = ...,  # type: ignore[type-arg, assignment]
    notifier: NotificationDispatcher = Depends(get_notification_service),
    geoip: GeoIpService = Depends(get_geoip_service),
) -> LoginService:
    session_repo = SessionRepository(db)
    anomaly = LoginAnomalyService(
        geoip=geoip,
        audit=AuditService(),
        session_repo=session_repo,
        notifier=notifier,
        redis=redis,
    )
    lockout = LoginLockoutService(redis, AuditService())
    session_cap = SessionCapEnforcer(session_repo, AuditService(), redis)
    breach_checker = PasswordBreachChecker(AuditService())
    return LoginService(
        UserRepository(db),
        PasskeyCredentialRepository(db),
        AuditService(),
        session_repo,
        anomaly,
        DeviceRepository(db),
        lockout,
        session_cap,
        breach_checker,
    )


# builds a refresh service for a request
def get_refresh_service(
    db: AsyncSession = Depends(get_db),
    redis: Annotated[aioredis.Redis, Depends(get_redis)] = ...,  # type: ignore[type-arg, assignment]
) -> RefreshService:
    return RefreshService(
        UserRepository(db),
        redis,
        AuditService(),
        SessionRepository(db),
        DeviceRepository(db),
    )


# builds a logout service for a request
def get_logout_service(
    db: AsyncSession = Depends(get_db),
    redis: Annotated[aioredis.Redis, Depends(get_redis)] = ...,  # type: ignore[type-arg, assignment]
) -> LogoutService:
    return LogoutService(redis, AuditService(), SessionRepository(db))


# builds a session service for a request
def get_session_service(
    db: AsyncSession = Depends(get_db),
    redis: Annotated[aioredis.Redis, Depends(get_redis)] = ...,  # type: ignore[type-arg, assignment]
    geoip: GeoIpService = Depends(get_geoip_service),
) -> SessionService:
    return SessionService(SessionRepository(db), redis, geoip)


# builds a profile service for a request
def get_profile_service(
    db: AsyncSession = Depends(get_db),
) -> ProfileService:
    return ProfileService(passkey_repo=PasskeyCredentialRepository(db))


# builds a registration service for a request
def get_registration_service(
    db: AsyncSession = Depends(get_db),
    notifier: NotificationDispatcher = Depends(get_notification_service),
    captcha: CaptchaService = Depends(get_captcha_service),
) -> RegistrationService:
    return RegistrationService(UserRepository(db), notifier, captcha, AuditService())


# builds an email verification service for a request
def get_email_verification_service(
    db: AsyncSession = Depends(get_db),
) -> EmailVerificationService:
    return EmailVerificationService(UserRepository(db), AuditService())


# builds a phone verification service for a request
def get_phone_verification_service(
    db: AsyncSession = Depends(get_db),
) -> PhoneVerificationService:
    return PhoneVerificationService(UserRepository(db), AuditService())


# builds a service that resends an email verification code
def get_resend_email_verification_service(
    db: AsyncSession = Depends(get_db),
    notifier: NotificationDispatcher = Depends(get_notification_service),
) -> ResendEmailVerificationService:
    return ResendEmailVerificationService(UserRepository(db), notifier)


# builds a service that resends a phone verification code
def get_resend_phone_otp_service(
    db: AsyncSession = Depends(get_db),
    notifier: NotificationDispatcher = Depends(get_notification_service),
) -> ResendPhoneOtpService:
    return ResendPhoneOtpService(UserRepository(db), notifier)


# builds a kyc submission service for a request
def get_kyc_service(
    db: AsyncSession = Depends(get_db),
    notifier: NotificationDispatcher = Depends(get_notification_service),
    ocr: OcrService = Depends(get_ocr_service),
) -> KycService:
    return KycService(UserRepository(db), notifier, AuditService(), ocr)


# builds a service that completes account setup
def get_complete_setup_service(
    db: AsyncSession = Depends(get_db),
) -> CompleteSetupService:
    return CompleteSetupService(
        UserRepository(db),
        PasskeyCredentialRepository(db),
        AuditService(),
        SessionRepository(db),
    )


# builds an email change service for a request
def get_email_change_service(
    db: AsyncSession = Depends(get_db),
    notifier: NotificationDispatcher = Depends(get_notification_service),
) -> EmailChangeService:
    return EmailChangeService(UserRepository(db), notifier, AuditService())


# builds a phone change service for a request
def get_phone_change_service(
    db: AsyncSession = Depends(get_db),
    notifier: NotificationDispatcher = Depends(get_notification_service),
) -> PhoneChangeService:
    return PhoneChangeService(UserRepository(db), notifier, AuditService())


# builds a password change service for a request
def get_password_change_service(
    db: AsyncSession = Depends(get_db),
    redis: Annotated[aioredis.Redis, Depends(get_redis)] = ...,  # type: ignore[type-arg, assignment]
) -> PasswordChangeService:
    return PasswordChangeService(
        UserRepository(db),
        SessionRepository(db),
        redis,
        AuditService(),
    )


# builds a forgot password service for a request
def get_forgot_password_service(
    db: AsyncSession = Depends(get_db),
    notifier: NotificationDispatcher = Depends(get_notification_service),
) -> ForgotPasswordService:
    return ForgotPasswordService(
        user_repo=UserRepository(db),
        notifier=notifier,
    )


# builds an account deletion service for a request
def get_deletion_service(
    db: AsyncSession = Depends(get_db),
    redis: Annotated[aioredis.Redis, Depends(get_redis)] = ...,  # type: ignore[type-arg, assignment]
) -> AccountDeletionService:
    return AccountDeletionService(
        UserRepository(db),
        SessionRepository(db),
        PasskeyCredentialRepository(db),
        redis,
        AuditService(),
    )


# builds an account recovery service for a request
def get_recovery_service(
    db: AsyncSession = Depends(get_db),
    redis: Annotated[aioredis.Redis, Depends(get_redis)] = ...,  # type: ignore[type-arg, assignment]
    notifier: NotificationDispatcher = Depends(get_notification_service),
    ocr: OcrService = Depends(get_ocr_service),
) -> RecoveryService:
    return RecoveryService(
        UserRepository(db),
        PasskeyCredentialRepository(db),
        SessionRepository(db),
        redis,
        notifier,
        AuditService(),
        ocr,
    )


# builds a fingerprint service for a request
def get_fingerprint_service(
    db: AsyncSession = Depends(get_db),
) -> FingerprintService:
    return FingerprintService(DeviceFingerprintRepository(db), AuditService())


# builds a device binding service for a request
def get_device_binding_service(
    db: AsyncSession = Depends(get_db),
    redis: Annotated[aioredis.Redis, Depends(get_redis)] = ...,  # type: ignore[type-arg, assignment]
) -> DeviceBindingService:
    return DeviceBindingService(DeviceRepository(db), redis, AuditService())


# builds a device attestation service for a request
def get_device_attestation_service(
    redis: Annotated[aioredis.Redis, Depends(get_redis)] = ...,  # type: ignore[type-arg, assignment]
) -> DeviceAttestationService:
    return DeviceAttestationService(build_attestation_verifier(), redis, AuditService())


# builds a device management service for a request
def get_device_service(
    db: AsyncSession = Depends(get_db),
    redis: Annotated[aioredis.Redis, Depends(get_redis)] = ...,  # type: ignore[type-arg, assignment]
) -> DeviceService:
    return DeviceService(
        DeviceRepository(db),
        SessionRepository(db),
        redis,
        AuditService(),
    )


# builds a passkey registration service for a request
def get_passkey_registration_service(
    db: AsyncSession = Depends(get_db),
    redis: Annotated[aioredis.Redis, Depends(get_redis)] = ...,  # type: ignore[type-arg, assignment]
) -> PasskeyRegistrationService:
    return PasskeyRegistrationService(PasskeyCredentialRepository(db), redis, AuditService())


# builds a passkey authentication service for a request
def get_passkey_authentication_service(
    db: AsyncSession = Depends(get_db),
    redis: Annotated[aioredis.Redis, Depends(get_redis)] = ...,  # type: ignore[type-arg, assignment]
) -> PasskeyAuthenticationService:
    return PasskeyAuthenticationService(
        PasskeyCredentialRepository(db),
        redis,
        UserRepository(db),
        AuditService(),
        SessionRepository(db),
    )


# builds a passkey reassertion service for a request
def get_passkey_reassertion_service(
    db: AsyncSession = Depends(get_db),
    redis: Annotated[aioredis.Redis, Depends(get_redis)] = ...,  # type: ignore[type-arg, assignment]
) -> PasskeyReassertionService:
    return PasskeyReassertionService(
        PasskeyCredentialRepository(db),
        redis,
        AuditService(),
        SessionRepository(db),
    )


# builds a passkey management service for a request
def get_passkey_management_service(
    db: AsyncSession = Depends(get_db),
) -> PasskeyManagementService:
    return PasskeyManagementService(PasskeyCredentialRepository(db), AuditService())


# builds a kyc review service for a request
def get_kyc_review_service(
    db: AsyncSession = Depends(get_db),
    notifier: NotificationDispatcher = Depends(get_notification_service),
) -> KycReviewService:
    return KycReviewService(UserRepository(db), notifier, AuditService())


# builds a login lockout service for a request
def get_login_lockout_service(
    redis: Annotated[aioredis.Redis, Depends(get_redis)] = ...,  # type: ignore[type-arg, assignment]
) -> LoginLockoutService:
    return LoginLockoutService(redis, AuditService())


# builds a user repository for a request
def get_user_repository(
    db: AsyncSession = Depends(get_db),
) -> UserRepository:
    return UserRepository(db)


# resolves the user a totp setup token identifies
async def get_totp_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = jwt_keys.verify(jwt_keys.TOTP, credentials.credentials)
    except (ExpiredSignatureError, InvalidTokenError) as exc:
        raise _CREDENTIALS_EXCEPTION from exc

    if payload.get("type") != "access" or payload.get("scope") != "totp":
        raise _CREDENTIALS_EXCEPTION

    subject = payload.get("sub")
    if not isinstance(subject, str):
        raise _CREDENTIALS_EXCEPTION

    try:
        user_id = uuid.UUID(subject)
    except ValueError as exc:
        raise _CREDENTIALS_EXCEPTION from exc

    user = await UserRepository(db).get_by_id(user_id)
    if user is None or not user.is_active:
        raise _CREDENTIALS_EXCEPTION
    return user


# builds a totp service for a request
def get_totp_service(
    db: AsyncSession = Depends(get_db),
) -> TotpService:
    return TotpService(UserRepository(db))
