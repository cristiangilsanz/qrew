from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.service.core.captcha import (
    CaptchaError,
    CaptchaService,
    build_captcha_service,
)
from com.qode.qrew.v1.service.core.database import get_db
from com.qode.qrew.v1.service.core.limiter import limiter
from com.qode.qrew.v1.service.repositories.user import UserRepository
from com.qode.qrew.v1.service.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    VerifyEmailRequest,
    VerifyPhoneRequest,
    VerifyResponse,
)
from com.qode.qrew.v1.service.services.login import LoginError, LoginService
from com.qode.qrew.v1.service.services.notification import (
    NotificationDispatcher,
    build_notification_dispatcher,
)
from com.qode.qrew.v1.service.services.registration import (
    RegistrationError,
    RegistrationService,
)
from com.qode.qrew.v1.service.services.verification import (
    EmailVerificationService,
    PhoneVerificationService,
    VerificationError,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _get_captcha_service() -> CaptchaService:
    """Build and return the captcha service."""
    return build_captcha_service()


def _get_notification_service() -> NotificationDispatcher:
    """Build and return the notification service."""
    return build_notification_dispatcher()


def get_registration_service(
    db: AsyncSession = Depends(get_db),
    notifier: NotificationDispatcher = Depends(_get_notification_service),
    captcha: CaptchaService = Depends(_get_captcha_service),
) -> RegistrationService:
    """Build and return the registration service."""
    return RegistrationService(UserRepository(db), notifier, captcha)


def get_email_verification_service(
    db: AsyncSession = Depends(get_db),
) -> EmailVerificationService:
    """Build and return the email verification service."""
    return EmailVerificationService(UserRepository(db))


def get_phone_verification_service(
    db: AsyncSession = Depends(get_db),
) -> PhoneVerificationService:
    """Build and return the phone verification service."""
    return PhoneVerificationService(UserRepository(db))


def get_login_service(
    db: AsyncSession = Depends(get_db),
) -> LoginService:
    """Build and return the login service."""
    return LoginService(UserRepository(db))


def _domain_error(
    exc: RegistrationError | VerificationError | CaptchaError | LoginError,
    http_status: int,
) -> HTTPException:
    """Convert a domain error to an HTTP exception."""
    return HTTPException(
        status_code=http_status,
        detail={"message": exc.message, "field": exc.field},
    )


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
@limiter.limit("5/hour")  # type: ignore[misc]
async def register(
    request: Request,
    body: RegisterRequest,
    service: RegistrationService = Depends(get_registration_service),
) -> RegisterResponse:
    """Register a new user account."""
    ip_address = request.client.host if request.client else "unknown"
    device_fingerprint = request.headers.get("X-Device-Fingerprint")

    try:
        return await service.register(body, ip_address, device_fingerprint)
    except CaptchaError as exc:
        raise _domain_error(exc, status.HTTP_400_BAD_REQUEST) from exc
    except RegistrationError as exc:
        raise _domain_error(exc, status.HTTP_409_CONFLICT) from exc


@router.post(
    "/verify-email",
    response_model=VerifyResponse,
    status_code=status.HTTP_200_OK,
    summary="Confirm an email address using the token from the verification link",
)
@limiter.limit("10/hour")  # type: ignore[misc]
async def verify_email(
    request: Request,
    body: VerifyEmailRequest,
    service: EmailVerificationService = Depends(get_email_verification_service),
) -> VerifyResponse:
    """Mark the user's email as verified."""
    try:
        await service.verify(body.token)
        return VerifyResponse(message="Email verified successfully.")
    except VerificationError as exc:
        raise _domain_error(exc, status.HTTP_400_BAD_REQUEST) from exc


@router.post(
    "/verify-phone",
    response_model=VerifyResponse,
    status_code=status.HTTP_200_OK,
    summary="Confirm a phone number using the token from the SMS",
)
@limiter.limit("5/hour")  # type: ignore[misc]
async def verify_phone(
    request: Request,
    body: VerifyPhoneRequest,
    service: PhoneVerificationService = Depends(get_phone_verification_service),
) -> VerifyResponse:
    """Mark the user's phone number as verified."""
    try:
        await service.verify(body.phone_number, body.otp)
        return VerifyResponse(message="Phone number verified successfully.")
    except VerificationError as exc:
        raise _domain_error(exc, status.HTTP_400_BAD_REQUEST) from exc


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Log in a registered user",
)
@limiter.limit("10/minute")  # type: ignore[misc]
async def login(
    request: Request,
    body: LoginRequest,
    service: LoginService = Depends(get_login_service),
) -> LoginResponse:
    """Log in as a registered user."""
    try:
        return await service.login(body)
    except LoginError as exc:
        raise _domain_error(exc, status.HTTP_401_UNAUTHORIZED) from exc
