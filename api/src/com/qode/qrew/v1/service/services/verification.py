from datetime import UTC, datetime

import structlog

from com.qode.qrew.v1.service.core.errors import DomainError
from com.qode.qrew.v1.service.repositories.user import UserRepository

logger = structlog.get_logger(__name__)


class VerificationError(DomainError):
    """A business-rule violation raised when a verification token or OTP is invalid."""


class EmailVerificationService:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    async def verify(self, token: str) -> None:
        """Mark the user's email as verified if the token is valid and unexpired."""
        user = await self._repo.get_by_email_verification_token(token)

        if user is None:
            await logger.awarning("email_verification_failed", reason="invalid_token")
            raise VerificationError(
                "Invalid or expired verification link", field="token"
            )
        if user.email_verified:
            await logger.awarning(
                "email_verification_failed",
                reason="already_verified",
                user_id=str(user.id),
            )
            raise VerificationError(
                "This email address is already verified", field="token"
            )
        if (
            user.email_verification_token_expires_at is None
            or user.email_verification_token_expires_at < datetime.now(UTC)
        ):
            await logger.awarning(
                "email_verification_failed",
                reason="token_expired",
                user_id=str(user.id),
            )
            raise VerificationError(
                "This verification link has expired. Request a new one", field="token"
            )

        user.email_verified = True
        user.email_verification_token = None
        user.email_verification_token_expires_at = None
        await self._repo.save(user)

        await logger.ainfo("email_verified", user_id=str(user.id))


class PhoneVerificationService:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    async def verify(self, phone_number: str, otp: str) -> None:
        """Mark the user's phone as verified if the verification OTP is valid
        and unexpired."""
        user = await self._repo.get_by_phone_number(phone_number)

        if user is None or user.phone_number_otp != otp:
            await logger.awarning(
                "phone_number_verification_failed", reason="invalid_otp"
            )
            raise VerificationError("Invalid or expired verification OTP", field="otp")
        if user.phone_number_verified:
            await logger.awarning(
                "phone_number_verification_failed",
                reason="already_verified",
                user_id=str(user.id),
            )
            raise VerificationError(
                "This phone number is already verified", field="otp"
            )
        if (
            user.phone_number_otp_expires_at is None
            or user.phone_number_otp_expires_at < datetime.now(UTC)
        ):
            await logger.awarning(
                "phone_number_verification_failed",
                reason="otp_expired",
                user_id=str(user.id),
            )
            raise VerificationError(
                "This verification OTP has expired. Request a new one", field="otp"
            )

        user.phone_number_verified = True
        user.phone_number_otp = None
        user.phone_number_otp_expires_at = None
        await self._repo.save(user)

        await logger.ainfo("phone_number_verified", user_id=str(user.id))
