import uuid
from datetime import UTC, datetime

import structlog

from com.qode.qrew.v1.service.core.captcha import CaptchaService
from com.qode.qrew.v1.service.core.errors import DomainError
from com.qode.qrew.v1.service.core.security import (
    email_verification_token_expiry,
    generate_otp,
    generate_token,
    hash_password,
    is_password_pwned,
    phone_number_otp_expiry,
)
from com.qode.qrew.v1.service.models.user import User
from com.qode.qrew.v1.service.repositories.user import UserRepository
from com.qode.qrew.v1.service.schemas.auth import RegisterRequest, RegisterResponse
from com.qode.qrew.v1.service.services.notification import NotificationService

logger = structlog.get_logger(__name__)


class RegistrationError(DomainError):
    """A business-rule violation raised when a registration cannot be completed."""


def _build_user(
    request: RegisterRequest,
    ip_address: str,
    device_fingerprint: str | None,
) -> User:
    """Construct a new User instance from the registration request."""
    now = datetime.now(UTC)
    return User(
        id=uuid.uuid4(),
        full_name=request.full_name,
        email=request.email,
        phone_number=request.phone_number,
        hashed_password=hash_password(request.password),
        email_verified=False,
        phone_number_verified=False,
        email_verification_token=generate_token(),
        email_verification_token_expires_at=email_verification_token_expiry(),
        phone_number_otp=generate_otp(),
        phone_number_otp_expires_at=phone_number_otp_expiry(),
        terms_accepted_at=now,
        registration_ip=ip_address,
        device_fingerprint=device_fingerprint,
        is_active=True,
    )


class RegistrationService:
    def __init__(
        self,
        repo: UserRepository,
        notifier: NotificationService,
        captcha: CaptchaService,
    ) -> None:
        self._repo = repo
        self._notifier = notifier
        self._captcha = captcha

    async def register(
        self,
        request: RegisterRequest,
        ip_address: str,
        device_fingerprint: str | None = None,
    ) -> RegisterResponse:
        """Create a new user account."""
        await self._assert_captcha_valid(request.captcha_token, ip_address)

        await self._assert_email_available(request.email)
        await self._assert_phone_available(request.phone_number)
        await self._assert_password_not_breached(request.password)

        user = _build_user(request, ip_address, device_fingerprint)
        created = await self._repo.create(user)

        await self._dispatch_verifications(created)

        await logger.ainfo(
            "user_registered",
            user_id=str(created.id),
            registration_ip=ip_address,
        )

        return RegisterResponse(
            id=str(created.id),
            message="Registration successful. Check your email to verify your account.",
        )

    async def _assert_captcha_valid(self, token: str, ip_address: str) -> None:
        """Raise CaptchaError if the captcha token is invalid."""
        await self._captcha.verify(token, ip_address)

    async def _assert_email_available(self, email: str) -> None:
        """Raise RegistrationError if the email is already registered."""
        if await self._repo.exists_by_email(email):
            await logger.awarning("registration_failed", reason="email_taken")
            raise RegistrationError("Email already registered", field="email")

    async def _assert_phone_available(self, phone_number: str) -> None:
        """Raise RegistrationError if the phone number is already registered."""
        if await self._repo.exists_by_phone(phone_number):
            await logger.awarning("registration_failed", reason="phone_number_taken")
            raise RegistrationError(
                "Phone number already registered", field="phone_number"
            )

    async def _assert_password_not_breached(self, password: str) -> None:
        """Raise RegistrationError if the password appears in a known breach."""
        if await is_password_pwned(password):
            await logger.awarning("registration_failed", reason="password_breached")
            raise RegistrationError(
                "This password has appeared in a known data breach. "
                "Choose a different one",
                field="password",
            )

    async def _dispatch_verifications(self, user: User) -> None:
        """Send verification link and OTP to the newly registered user."""
        assert user.email_verification_token is not None
        assert user.phone_number_otp is not None
        await self._notifier.send_email_verification_link(
            user.email,
            user.full_name,
            user.email_verification_token,
        )
        await self._notifier.send_sms_otp(
            user.phone_number,
            user.phone_number_otp,
        )
