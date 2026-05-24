import uuid
from typing import Annotated

import redis.asyncio as aioredis
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.service.core.auth import get_current_user, get_setup_or_full_user
from com.qode.qrew.v1.service.core.captcha import (
    CaptchaError,
    CaptchaService,
    build_captcha_service,
)
from com.qode.qrew.v1.service.core.database import get_db
from com.qode.qrew.v1.service.core.limiter import limiter
from com.qode.qrew.v1.service.core.redis import get_redis
from com.qode.qrew.v1.service.models.user import User
from com.qode.qrew.v1.service.repositories.passkey import PasskeyCredentialRepository
from com.qode.qrew.v1.service.repositories.session import SessionRepository
from com.qode.qrew.v1.service.repositories.user import UserRepository
from com.qode.qrew.v1.service.schemas.auth import (
    ChangeEmailRequest,
    ChangeEmailResponse,
    ChangePasswordRequest,
    ChangePasswordResponse,
    ConfirmEmailChangeRequest,
    KycUploadResponse,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    LogoutResponse,
    PasskeyAuthenticationBeginRequest,
    PasskeyAuthenticationCompleteRequest,
    PasskeyRegistrationCompleteRequest,
    PasskeyRegistrationCompleteResponse,
    RefreshRequest,
    RefreshResponse,
    RegisterRequest,
    RegisterResponse,
    ResendEmailVerificationRequest,
    ResendPhoneOtpRequest,
    ResendResponse,
    VerifyEmailRequest,
    VerifyPhoneRequest,
    VerifyResponse,
)
from com.qode.qrew.v1.service.schemas.passkey import (
    PasskeyListResponse,
    PasskeyRenameRequest,
    PasskeyResponse,
)
from com.qode.qrew.v1.service.schemas.session import (
    RevokeAllResponse,
    SessionListResponse,
)
from com.qode.qrew.v1.service.services.audit import AuditService
from com.qode.qrew.v1.service.services.complete_setup import (
    CompleteSetupService,
    SetupError,
)
from com.qode.qrew.v1.service.services.email_change import (
    EmailChangeError,
    EmailChangeService,
)
from com.qode.qrew.v1.service.services.kyc import KycError, KycService
from com.qode.qrew.v1.service.services.login import LoginError, LoginService
from com.qode.qrew.v1.service.services.logout import LogoutError, LogoutService
from com.qode.qrew.v1.service.services.notification import (
    NotificationDispatcher,
    build_notification_dispatcher,
)
from com.qode.qrew.v1.service.services.passkey import PasskeyError, PasskeyService
from com.qode.qrew.v1.service.services.password_change import (
    PasswordChangeError,
    PasswordChangeService,
)
from com.qode.qrew.v1.service.services.refresh import RefreshError, RefreshService
from com.qode.qrew.v1.service.services.registration import (
    RegistrationError,
    RegistrationService,
)
from com.qode.qrew.v1.service.services.resend_verification import (
    ResendEmailVerificationService,
    ResendError,
    ResendPhoneOtpService,
)
from com.qode.qrew.v1.service.services.session import SessionError, SessionService
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
    return RegistrationService(UserRepository(db), notifier, captcha, AuditService())


def get_email_verification_service(
    db: AsyncSession = Depends(get_db),
) -> EmailVerificationService:
    """Build and return the email verification service."""
    return EmailVerificationService(UserRepository(db), AuditService())


def get_phone_verification_service(
    db: AsyncSession = Depends(get_db),
) -> PhoneVerificationService:
    """Build and return the phone verification service."""
    return PhoneVerificationService(UserRepository(db), AuditService())


def get_login_service(
    db: AsyncSession = Depends(get_db),
) -> LoginService:
    """Build and return the login service."""
    return LoginService(
        UserRepository(db),
        PasskeyCredentialRepository(db),
        AuditService(),
        SessionRepository(db),
    )


def get_refresh_service(
    db: AsyncSession = Depends(get_db),
    redis: Annotated[aioredis.Redis, Depends(get_redis)] = ...,  # type: ignore[type-arg, assignment]
) -> RefreshService:
    """Build and return the refresh service."""
    return RefreshService(
        UserRepository(db), redis, AuditService(), SessionRepository(db)
    )


def get_logout_service(
    db: AsyncSession = Depends(get_db),
    redis: Annotated[aioredis.Redis, Depends(get_redis)] = ...,  # type: ignore[type-arg, assignment]
) -> LogoutService:
    """Build and return the logout service."""
    return LogoutService(redis, AuditService(), SessionRepository(db))


def get_session_service(
    db: AsyncSession = Depends(get_db),
    redis: Annotated[aioredis.Redis, Depends(get_redis)] = ...,  # type: ignore[type-arg, assignment]
) -> SessionService:
    """Build and return the session service."""
    return SessionService(SessionRepository(db), redis)


def get_resend_email_verification_service(
    db: AsyncSession = Depends(get_db),
    notifier: NotificationDispatcher = Depends(_get_notification_service),
) -> ResendEmailVerificationService:
    """Build and return the resend email verification service."""
    return ResendEmailVerificationService(UserRepository(db), notifier)


def get_resend_phone_otp_service(
    db: AsyncSession = Depends(get_db),
    notifier: NotificationDispatcher = Depends(_get_notification_service),
) -> ResendPhoneOtpService:
    """Build and return the resend phone OTP service."""
    return ResendPhoneOtpService(UserRepository(db), notifier)


def get_kyc_service(
    db: AsyncSession = Depends(get_db),
    notifier: NotificationDispatcher = Depends(_get_notification_service),
) -> KycService:
    """Build and return the KYC service."""
    return KycService(UserRepository(db), notifier, AuditService())


def get_passkey_service(
    db: AsyncSession = Depends(get_db),
    redis: Annotated[aioredis.Redis, Depends(get_redis)] = ...,  # type: ignore[type-arg, assignment]
) -> PasskeyService:
    """Build and return the passkey service."""
    return PasskeyService(
        PasskeyCredentialRepository(db),
        redis,
        UserRepository(db),
        AuditService(),
        SessionRepository(db),
    )


def get_complete_setup_service(
    db: AsyncSession = Depends(get_db),
) -> CompleteSetupService:
    """Build and return the complete-setup service."""
    return CompleteSetupService(
        UserRepository(db),
        PasskeyCredentialRepository(db),
        AuditService(),
        SessionRepository(db),
    )


def get_email_change_service(
    db: AsyncSession = Depends(get_db),
    notifier: NotificationDispatcher = Depends(_get_notification_service),
) -> EmailChangeService:
    """Build and return the email change service."""
    return EmailChangeService(UserRepository(db), notifier, AuditService())


def get_password_change_service(
    db: AsyncSession = Depends(get_db),
    redis: Annotated[aioredis.Redis, Depends(get_redis)] = ...,  # type: ignore[type-arg, assignment]
) -> PasswordChangeService:
    """Build and return the password change service."""
    return PasswordChangeService(
        UserRepository(db),
        SessionRepository(db),
        redis,
        AuditService(),
    )


_DomainError = (
    RegistrationError
    | VerificationError
    | CaptchaError
    | LoginError
    | RefreshError
    | LogoutError
    | ResendError
    | KycError
    | PasskeyError
    | SetupError
    | SessionError
    | PasswordChangeError
    | EmailChangeError
)


def _domain_error(exc: _DomainError, http_status: int) -> HTTPException:
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
    summary="Confirm a phone number using the OTP from the SMS",
)
@limiter.limit("5/hour")  # type: ignore[misc]
async def verify_phone(
    request: Request,
    body: VerifyPhoneRequest,
    current_user: User = Depends(get_setup_or_full_user),
    service: PhoneVerificationService = Depends(get_phone_verification_service),
) -> VerifyResponse:
    """Mark the authenticated user's phone number as verified."""
    if body.phone_number != current_user.phone_number:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": "Phone number does not match your account",
                "field": "phone_number",
            },
        )
    try:
        await service.verify(body.phone_number, body.otp)
        return VerifyResponse(message="Phone number verified successfully.")
    except VerificationError as exc:
        raise _domain_error(exc, status.HTTP_400_BAD_REQUEST) from exc


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Log in as a registered user",
)
@limiter.limit("10/minute")  # type: ignore[misc]
async def login(
    request: Request,
    body: LoginRequest,
    service: LoginService = Depends(get_login_service),
) -> LoginResponse:
    """Log in as a registered user."""
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    device_fingerprint = request.headers.get("X-Device-Fingerprint")
    try:
        return await service.login(body, ip_address, user_agent, device_fingerprint)
    except LoginError as exc:
        raise _domain_error(exc, status.HTTP_401_UNAUTHORIZED) from exc


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
    """Issue a new access token from a valid refresh token."""
    try:
        return await service.refresh(body)
    except RefreshError as exc:
        raise _domain_error(exc, status.HTTP_401_UNAUTHORIZED) from exc


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
    """Blacklist the refresh token's JTI so it cannot be reused."""
    try:
        await service.logout(body.refresh_token)
        return LogoutResponse(message="Logged out successfully.")
    except LogoutError as exc:
        raise _domain_error(exc, status.HTTP_401_UNAUTHORIZED) from exc


@router.post(
    "/resend-email-verification",
    response_model=ResendResponse,
    status_code=status.HTTP_200_OK,
    summary="Resend the email verification link",
)
@limiter.limit("3/hour")  # type: ignore[misc]
async def resend_email_verification(
    request: Request,
    body: ResendEmailVerificationRequest,
    service: ResendEmailVerificationService = Depends(
        get_resend_email_verification_service
    ),
) -> ResendResponse:
    """Send a fresh email verification link to an unverified account."""
    try:
        await service.resend(body.email)
        return ResendResponse(message="Verification link sent. Check your inbox.")
    except ResendError as exc:
        raise _domain_error(exc, status.HTTP_400_BAD_REQUEST) from exc


@router.post(
    "/resend-phone-otp",
    response_model=ResendResponse,
    status_code=status.HTTP_200_OK,
    summary="Resend the phone verification OTP",
)
@limiter.limit("3/hour")  # type: ignore[misc]
async def resend_phone_otp(
    request: Request,
    body: ResendPhoneOtpRequest,
    service: ResendPhoneOtpService = Depends(get_resend_phone_otp_service),
) -> ResendResponse:
    """Send a fresh OTP to an unverified phone number."""
    try:
        await service.resend(body.phone_number)
        return ResendResponse(message="Verification OTP sent. Check your SMS.")
    except ResendError as exc:
        raise _domain_error(exc, status.HTTP_400_BAD_REQUEST) from exc


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
    """Hash and store the national ID document; mark KYC as pending."""
    content = await document.read()
    try:
        final_status = await service.upload(current_user, content)
        return KycUploadResponse(
            message="KYC document submitted for review.",
            kyc_status=final_status,
        )
    except KycError as exc:
        raise _domain_error(exc, status.HTTP_400_BAD_REQUEST) from exc


@router.post(
    "/passkey/register/begin",
    status_code=status.HTTP_200_OK,
    summary="Begin WebAuthn passkey registration",
)
@limiter.limit("10/hour")  # type: ignore[misc]
async def passkey_register_begin(
    request: Request,
    current_user: User = Depends(get_setup_or_full_user),
    service: PasskeyService = Depends(get_passkey_service),
) -> Response:
    """Generate WebAuthn registration options for the authenticated user."""
    options_json = await service.begin_registration(current_user)
    return Response(content=options_json, media_type="application/json")


@router.post(
    "/passkey/register/complete",
    response_model=PasskeyRegistrationCompleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Complete WebAuthn passkey registration",
)
@limiter.limit("10/hour")  # type: ignore[misc]
async def passkey_register_complete(
    request: Request,
    body: PasskeyRegistrationCompleteRequest,
    current_user: User = Depends(get_setup_or_full_user),
    service: PasskeyService = Depends(get_passkey_service),
) -> PasskeyRegistrationCompleteResponse:
    """Verify the attestation response and store the passkey credential."""
    try:
        await service.complete_registration(current_user, body)
        return PasskeyRegistrationCompleteResponse(
            message="Passkey registered successfully."
        )
    except PasskeyError as exc:
        raise _domain_error(exc, status.HTTP_400_BAD_REQUEST) from exc


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
    """Verify all onboarding steps are done and return full access + refresh tokens."""
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    device_fingerprint = request.headers.get("X-Device-Fingerprint")
    try:
        return await service.complete(
            current_user, ip_address, user_agent, device_fingerprint
        )
    except SetupError as exc:
        raise _domain_error(exc, status.HTTP_400_BAD_REQUEST) from exc


@router.post(
    "/passkey/authenticate/begin",
    status_code=status.HTTP_200_OK,
    summary="Begin WebAuthn passkey authentication",
)
@limiter.limit("10/minute")  # type: ignore[misc]
async def passkey_authenticate_begin(
    request: Request,
    body: PasskeyAuthenticationBeginRequest,
    service: PasskeyService = Depends(get_passkey_service),
) -> Response:
    """Generate WebAuthn assertion options for the given email address."""
    try:
        options_json = await service.begin_authentication(body.email)
        return Response(content=options_json, media_type="application/json")
    except PasskeyError as exc:
        raise _domain_error(exc, status.HTTP_400_BAD_REQUEST) from exc


@router.post(
    "/passkey/authenticate/complete",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Complete WebAuthn passkey authentication",
)
@limiter.limit("10/minute")  # type: ignore[misc]
async def passkey_authenticate_complete(
    request: Request,
    body: PasskeyAuthenticationCompleteRequest,
    service: PasskeyService = Depends(get_passkey_service),
) -> LoginResponse:
    """Verify the assertion response and return access tokens."""
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    device_fingerprint = request.headers.get("X-Device-Fingerprint")
    try:
        return await service.complete_authentication(
            body, ip_address, user_agent, device_fingerprint
        )
    except PasskeyError as exc:
        raise _domain_error(exc, status.HTTP_400_BAD_REQUEST) from exc


# ── Session management ────────────────────────────────────────────────────────


@router.get(
    "/sessions",
    response_model=SessionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all active sessions for the current user",
)
@limiter.limit("20/minute")  # type: ignore[misc]
async def list_sessions(
    request: Request,
    current_user: User = Depends(get_current_user),
    service: SessionService = Depends(get_session_service),
) -> SessionListResponse:
    """Return all active sessions for the authenticated user."""
    sessions = await service.list_sessions(current_user.id)
    return SessionListResponse(sessions=sessions)


@router.delete(
    "/sessions/{jti}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke a specific session by JTI",
)
@limiter.limit("20/minute")  # type: ignore[misc]
async def revoke_session(
    request: Request,
    jti: str,
    current_user: User = Depends(get_current_user),
    service: SessionService = Depends(get_session_service),
) -> None:
    """Blacklist the given JTI and remove the session row."""
    try:
        await service.revoke_session(jti, current_user.id)
    except SessionError as exc:
        raise _domain_error(exc, status.HTTP_404_NOT_FOUND) from exc


@router.post(
    "/sessions/revoke-all",
    response_model=RevokeAllResponse,
    status_code=status.HTTP_200_OK,
    summary="Revoke all sessions for the current user",
)
@limiter.limit("10/minute")  # type: ignore[misc]
async def revoke_all_sessions(
    request: Request,
    current_user: User = Depends(get_current_user),
    service: SessionService = Depends(get_session_service),
) -> RevokeAllResponse:
    """Invalidate every refresh token for the authenticated user."""
    await service.revoke_all(current_user.id)
    return RevokeAllResponse(message="All sessions have been revoked.")


# ── Passkey management ────────────────────────────────────────────────────────


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
    service: PasskeyService = Depends(get_passkey_service),
) -> PasskeyListResponse:
    """Return all passkeys registered by the authenticated user."""
    return await service.list_passkeys(current_user.id)


@router.delete(
    "/passkeys/{passkey_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a passkey by ID",
)
@limiter.limit("20/minute")  # type: ignore[misc]
async def delete_passkey(
    request: Request,
    passkey_id: str,
    current_user: User = Depends(get_current_user),
    service: PasskeyService = Depends(get_passkey_service),
) -> None:
    """Remove a passkey; refuses if it is the user's last one (409)."""
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
        raise _domain_error(exc, http_status) from exc


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
    service: PasskeyService = Depends(get_passkey_service),
) -> PasskeyResponse:
    """Update the display name of a passkey credential."""
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
        raise _domain_error(exc, status.HTTP_404_NOT_FOUND) from exc


# ── Account management ────────────────────────────────────────────────────────


@router.post(
    "/change-password",
    response_model=ChangePasswordResponse,
    status_code=status.HTTP_200_OK,
    summary="Change the authenticated user's password",
)
@limiter.limit("5/hour")  # type: ignore[misc]
async def change_password(
    request: Request,
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    service: PasswordChangeService = Depends(get_password_change_service),
) -> ChangePasswordResponse:
    """Verify the current password and replace it; revokes all active sessions."""
    try:
        await service.change_password(
            current_user, body.current_password, body.new_password
        )
        return ChangePasswordResponse(message="Password changed successfully.")
    except PasswordChangeError as exc:
        raise _domain_error(exc, status.HTTP_400_BAD_REQUEST) from exc


@router.post(
    "/change-email",
    response_model=ChangeEmailResponse,
    status_code=status.HTTP_200_OK,
    summary="Request an email address change",
)
@limiter.limit("3/hour")  # type: ignore[misc]
async def change_email(
    request: Request,
    body: ChangeEmailRequest,
    current_user: User = Depends(get_current_user),
    service: EmailChangeService = Depends(get_email_change_service),
) -> ChangeEmailResponse:
    """Store a pending email change and send a confirmation link to the new address."""
    try:
        await service.request_change(
            current_user, body.new_email, body.current_password
        )
        return ChangeEmailResponse(
            message="Confirmation link sent to your new email address."
        )
    except EmailChangeError as exc:
        raise _domain_error(exc, status.HTTP_400_BAD_REQUEST) from exc


@router.post(
    "/confirm-email-change",
    response_model=ChangeEmailResponse,
    status_code=status.HTTP_200_OK,
    summary="Confirm an email address change using the token from the link",
)
@limiter.limit("10/hour")  # type: ignore[misc]
async def confirm_email_change(
    request: Request,
    body: ConfirmEmailChangeRequest,
    service: EmailChangeService = Depends(get_email_change_service),
) -> ChangeEmailResponse:
    """Swap the pending email into the active email field."""
    try:
        await service.confirm_change(body.token)
        return ChangeEmailResponse(message="Email address updated successfully.")
    except EmailChangeError as exc:
        raise _domain_error(exc, status.HTTP_400_BAD_REQUEST) from exc
