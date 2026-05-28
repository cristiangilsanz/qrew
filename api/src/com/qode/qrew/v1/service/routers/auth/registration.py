from fastapi import APIRouter, Depends, HTTPException, Request, status

from com.qode.qrew.v1.service.core.auth.auth import get_setup_or_full_user
from com.qode.qrew.v1.service.core.infra.limiter import limiter
from com.qode.qrew.v1.service.core.registration.captcha import CaptchaError
from com.qode.qrew.v1.service.models.auth.user import User
from com.qode.qrew.v1.service.schemas.registration.registration import (
    RegisterRequest,
    RegisterResponse,
    ResendEmailVerificationRequest,
    ResendPhoneOtpRequest,
    ResendResponse,
    VerifyEmailRequest,
    VerifyPhoneRequest,
    VerifyResponse,
)
from com.qode.qrew.v1.service.services.registration.registration import (
    RegistrationError,
    RegistrationService,
)
from com.qode.qrew.v1.service.services.registration.resend_verification import (
    ResendEmailVerificationService,
    ResendError,
    ResendPhoneOtpService,
)
from com.qode.qrew.v1.service.services.registration.verification import (
    EmailVerificationService,
    PhoneVerificationService,
    VerificationError,
)

from ._deps import (
    domain_error,
    get_email_verification_service,
    get_phone_verification_service,
    get_registration_service,
    get_resend_email_verification_service,
    get_resend_phone_otp_service,
)

router = APIRouter()


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
        raise domain_error(exc.message, exc.field, status.HTTP_400_BAD_REQUEST) from exc
    except RegistrationError as exc:
        raise domain_error(exc.message, exc.field, status.HTTP_409_CONFLICT) from exc


@router.post(
    "/verify-email",
    response_model=VerifyResponse,
    status_code=status.HTTP_200_OK,
    summary="Confirm an email address using the verification token",
)
@limiter.limit("10/hour")  # type: ignore[misc]
async def verify_email(
    request: Request,
    body: VerifyEmailRequest,
    service: EmailVerificationService = Depends(get_email_verification_service),
) -> VerifyResponse:
    """Confirm an email address."""
    try:
        await service.verify(body.token)
        return VerifyResponse(message="Email verified successfully.")
    except VerificationError as exc:
        raise domain_error(exc.message, exc.field, status.HTTP_400_BAD_REQUEST) from exc


@router.post(
    "/verify-phone",
    response_model=VerifyResponse,
    status_code=status.HTTP_200_OK,
    summary="Confirm a phone number using the OTP",
)
@limiter.limit("5/hour")  # type: ignore[misc]
async def verify_phone(
    request: Request,
    body: VerifyPhoneRequest,
    current_user: User = Depends(get_setup_or_full_user),
    service: PhoneVerificationService = Depends(get_phone_verification_service),
) -> VerifyResponse:
    """Confirm a phone number."""
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
        raise domain_error(exc.message, exc.field, status.HTTP_400_BAD_REQUEST) from exc


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
    """Send a fresh email verification link."""
    try:
        await service.resend(body.email)
        return ResendResponse(message="Verification link sent. Check your inbox.")
    except ResendError as exc:
        raise domain_error(exc.message, exc.field, status.HTTP_400_BAD_REQUEST) from exc


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
    """Send a fresh OTP to a phone number."""
    try:
        await service.resend(body.phone_number)
        return ResendResponse(message="Verification OTP sent. Check your SMS.")
    except ResendError as exc:
        raise domain_error(exc.message, exc.field, status.HTTP_400_BAD_REQUEST) from exc
