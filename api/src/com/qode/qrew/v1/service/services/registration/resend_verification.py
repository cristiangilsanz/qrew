import structlog

from com.qode.qrew.v1.service.core.auth.security import (
    email_verification_token_expiry,
    generate_otp,
    generate_token,
    phone_number_otp_expiry,
)
from com.qode.qrew.v1.service.core.infra.errors import DomainError
from com.qode.qrew.v1.service.repositories.auth.user import UserRepository
from com.qode.qrew.v1.service.services.infra.notification import NotificationService

logger = structlog.get_logger(__name__)


class ResendError(DomainError):
    """Raised when a verification resend cannot be completed."""


class ResendEmailVerificationService:
    def __init__(self, repo: UserRepository, notifier: NotificationService) -> None:
        self._repo = repo
        self._notifier = notifier

    async def resend(self, email: str) -> None:
        """Generate a fresh email verification token and dispatch the link."""
        user = await self._repo.get_by_email(email)

        if user is None:
            await logger.awarning("resend_email_failed", reason="user_not_found")
            raise ResendError("No account found with that email address", field="email")
        if user.email_verified:
            await logger.awarning(
                "resend_email_failed",
                reason="already_verified",
                user_id=str(user.id),
            )
            raise ResendError("This email address is already verified", field="email")

        token = generate_token()
        user.email_verification_token = token
        user.email_verification_token_expires_at = email_verification_token_expiry()
        await self._repo.save(user)

        await self._notifier.send_email_verification_link(
            user.email, user.full_name, token
        )
        await logger.ainfo("email_verification_resent", user_id=str(user.id))


class ResendPhoneOtpService:
    def __init__(self, repo: UserRepository, notifier: NotificationService) -> None:
        self._repo = repo
        self._notifier = notifier

    async def resend(self, phone_number: str) -> None:
        """Generate a fresh OTP and dispatch it via SMS."""
        user = await self._repo.get_by_phone_number(phone_number)

        if user is None:
            await logger.awarning("resend_otp_failed", reason="user_not_found")
            raise ResendError(
                "No account found with that phone number", field="phone_number"
            )
        if user.phone_number_verified:
            await logger.awarning(
                "resend_otp_failed",
                reason="already_verified",
                user_id=str(user.id),
            )
            raise ResendError(
                "This phone number is already verified", field="phone_number"
            )

        otp = generate_otp()
        user.phone_number_otp = otp
        user.phone_number_otp_expires_at = phone_number_otp_expiry()
        await self._repo.save(user)

        await self._notifier.send_sms_otp(user.phone_number, otp)
        await logger.ainfo("phone_otp_resent", user_id=str(user.id))
