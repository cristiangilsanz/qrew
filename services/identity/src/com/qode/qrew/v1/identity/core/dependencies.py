import uuid
from collections.abc import AsyncGenerator
from typing import Annotated

import redis.asyncio as aioredis
import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import ExpiredSignatureError, InvalidTokenError
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.identity.core.config import settings
from com.qode.qrew.v1.identity.core.database import get_db
from com.qode.qrew.v1.identity.core.utils.geoip import GeoIpService
from com.qode.qrew.v1.identity.models.session import Session
from com.qode.qrew.v1.identity.models.user import User
from com.qode.qrew.v1.identity.repositories.audit import AuditRepository
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

logger = structlog.get_logger(__name__)

limiter = Limiter(key_func=get_remote_address, default_limits=[])

_bearer = HTTPBearer()

_CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail={"message": "Invalid or expired token", "field": None},
)

_SETUP_REQUIRED_EXCEPTION = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail={
        "message": "Setup not complete. Use /auth/complete-setup first.",
        "field": None,
    },
)


async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:  # type: ignore[type-arg]
    client: aioredis.Redis = aioredis.from_url(  # type: ignore[type-arg]
        settings.redis_url, decode_responses=False
    )
    try:
        yield client
    finally:
        await client.aclose()


# ---------------------------------------------------------------------------
# User / session resolution
# ---------------------------------------------------------------------------


async def _resolve_user(
    credentials: HTTPAuthorizationCredentials,
    db: AsyncSession,
    *,
    allow_setup: bool,
) -> User:
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


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    db: AsyncSession = Depends(get_db),
) -> User:
    return await _resolve_user(credentials, db, allow_setup=False)


async def get_setup_or_full_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    db: AsyncSession = Depends(get_db),
) -> User:
    return await _resolve_user(credentials, db, allow_setup=True)


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


async def get_admin_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": "Admin access required", "field": None},
        )
    return current_user


def domain_error(message: str, field: str | None, http_status: int) -> HTTPException:
    return HTTPException(status_code=http_status, detail={"message": message, "field": field})


# ---------------------------------------------------------------------------
# Shared singletons
# ---------------------------------------------------------------------------


def get_captcha_service() -> CaptchaService:
    return build_captcha_service()


def get_notification_service() -> NotificationDispatcher:
    return build_notification_dispatcher()


def get_geoip_service() -> GeoIpService:
    return GeoIpService(settings.geoip_db_path)


def get_ocr_service() -> OcrService:
    return OcrService()


# ---------------------------------------------------------------------------
# Auth service factories
# ---------------------------------------------------------------------------


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


def get_logout_service(
    db: AsyncSession = Depends(get_db),
    redis: Annotated[aioredis.Redis, Depends(get_redis)] = ...,  # type: ignore[type-arg, assignment]
) -> LogoutService:
    return LogoutService(redis, AuditService(), SessionRepository(db))


def get_session_service(
    db: AsyncSession = Depends(get_db),
    redis: Annotated[aioredis.Redis, Depends(get_redis)] = ...,  # type: ignore[type-arg, assignment]
) -> SessionService:
    return SessionService(SessionRepository(db), redis)


def get_profile_service(
    db: AsyncSession = Depends(get_db),
) -> ProfileService:
    return ProfileService(
        passkey_repo=PasskeyCredentialRepository(db),
        audit_repo=AuditRepository(db),
    )


# ---------------------------------------------------------------------------
# Registration service factories
# ---------------------------------------------------------------------------


def get_registration_service(
    db: AsyncSession = Depends(get_db),
    notifier: NotificationDispatcher = Depends(get_notification_service),
    captcha: CaptchaService = Depends(get_captcha_service),
) -> RegistrationService:
    return RegistrationService(UserRepository(db), notifier, captcha, AuditService())


def get_email_verification_service(
    db: AsyncSession = Depends(get_db),
) -> EmailVerificationService:
    return EmailVerificationService(UserRepository(db), AuditService())


def get_phone_verification_service(
    db: AsyncSession = Depends(get_db),
) -> PhoneVerificationService:
    return PhoneVerificationService(UserRepository(db), AuditService())


def get_resend_email_verification_service(
    db: AsyncSession = Depends(get_db),
    notifier: NotificationDispatcher = Depends(get_notification_service),
) -> ResendEmailVerificationService:
    return ResendEmailVerificationService(UserRepository(db), notifier)


def get_resend_phone_otp_service(
    db: AsyncSession = Depends(get_db),
    notifier: NotificationDispatcher = Depends(get_notification_service),
) -> ResendPhoneOtpService:
    return ResendPhoneOtpService(UserRepository(db), notifier)


# ---------------------------------------------------------------------------
# Setup / KYC service factories
# ---------------------------------------------------------------------------


def get_kyc_service(
    db: AsyncSession = Depends(get_db),
    notifier: NotificationDispatcher = Depends(get_notification_service),
    ocr: OcrService = Depends(get_ocr_service),
) -> KycService:
    return KycService(UserRepository(db), notifier, AuditService(), ocr)


def get_complete_setup_service(
    db: AsyncSession = Depends(get_db),
) -> CompleteSetupService:
    return CompleteSetupService(
        UserRepository(db),
        PasskeyCredentialRepository(db),
        AuditService(),
        SessionRepository(db),
    )


# ---------------------------------------------------------------------------
# Account service factories
# ---------------------------------------------------------------------------


def get_email_change_service(
    db: AsyncSession = Depends(get_db),
    notifier: NotificationDispatcher = Depends(get_notification_service),
) -> EmailChangeService:
    return EmailChangeService(UserRepository(db), notifier, AuditService())


def get_phone_change_service(
    db: AsyncSession = Depends(get_db),
    notifier: NotificationDispatcher = Depends(get_notification_service),
) -> PhoneChangeService:
    return PhoneChangeService(UserRepository(db), notifier, AuditService())


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


# ---------------------------------------------------------------------------
# Device service factories
# ---------------------------------------------------------------------------


def get_fingerprint_service(
    db: AsyncSession = Depends(get_db),
) -> FingerprintService:
    return FingerprintService(DeviceFingerprintRepository(db), AuditService())


def get_device_binding_service(
    db: AsyncSession = Depends(get_db),
    redis: Annotated[aioredis.Redis, Depends(get_redis)] = ...,  # type: ignore[type-arg, assignment]
) -> DeviceBindingService:
    return DeviceBindingService(DeviceRepository(db), redis, AuditService())


def get_device_attestation_service(
    redis: Annotated[aioredis.Redis, Depends(get_redis)] = ...,  # type: ignore[type-arg, assignment]
) -> DeviceAttestationService:
    return DeviceAttestationService(build_attestation_verifier(), redis, AuditService())


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


# ---------------------------------------------------------------------------
# Passkey service factories
# ---------------------------------------------------------------------------


def get_passkey_registration_service(
    db: AsyncSession = Depends(get_db),
    redis: Annotated[aioredis.Redis, Depends(get_redis)] = ...,  # type: ignore[type-arg, assignment]
) -> PasskeyRegistrationService:
    return PasskeyRegistrationService(PasskeyCredentialRepository(db), redis, AuditService())


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


def get_passkey_management_service(
    db: AsyncSession = Depends(get_db),
) -> PasskeyManagementService:
    return PasskeyManagementService(PasskeyCredentialRepository(db), AuditService())


# ---------------------------------------------------------------------------
# Admin service factories
# ---------------------------------------------------------------------------


def get_kyc_review_service(
    db: AsyncSession = Depends(get_db),
    notifier: NotificationDispatcher = Depends(get_notification_service),
) -> KycReviewService:
    return KycReviewService(UserRepository(db), notifier, AuditService())


def get_login_lockout_service(
    redis: Annotated[aioredis.Redis, Depends(get_redis)] = ...,  # type: ignore[type-arg, assignment]
) -> LoginLockoutService:
    return LoginLockoutService(redis, AuditService())


def get_user_repository(
    db: AsyncSession = Depends(get_db),
) -> UserRepository:
    return UserRepository(db)
