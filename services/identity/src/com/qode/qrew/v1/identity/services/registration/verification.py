from datetime import UTC, datetime

import structlog

from com.qode.qrew.v1.identity.core.infra.errors import DomainError
from com.qode.qrew.v1.identity.models.audit.audit import AuditAction
from com.qode.qrew.v1.identity.repositories.auth.user import UserRepository
from com.qode.qrew.v1.identity.services.audit import AuditService

logger = structlog.get_logger(__name__)


class VerificationError(DomainError):
    """Raised when a verification token or one-time password is invalid."""


class EmailVerificationService:
    def __init__(self, repo: UserRepository, audit: AuditService) -> None:
        self._repo = repo
        self._audit = audit

    async def verify(self, token: str) -> None:
        """Verify an email address with the provided verification token."""
        user = await self._repo.get_by_email_verification_token(token)

        if user is None:
            await logger.awarning("email_verification_failed", reason="invalid_token")
            raise VerificationError("Invalid or expired verification link", field="token")
        if user.email_verified:
            await logger.awarning(
                "email_verification_failed",
                reason="already_verified",
                user_id=str(user.id),
            )
            raise VerificationError("This email address is already verified", field="token")
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
        try:
            await self._audit.record(
                action=AuditAction.VERIFY_EMAIL,
                actor_id=user.id,
                entity_type="user",
                entity_id=str(user.id),
            )
        except Exception:
            await logger.awarning("audit_write_failed", action=AuditAction.VERIFY_EMAIL)


class PhoneVerificationService:
    def __init__(self, repo: UserRepository, audit: AuditService) -> None:
        self._repo = repo
        self._audit = audit

    async def verify(self, phone_number: str, otp: str) -> None:
        """Verify a phone number with the provided one-time password."""
        user = await self._repo.get_by_phone_number(phone_number)

        if user is None or user.phone_number_otp != otp:
            await logger.awarning("phone_number_verification_failed", reason="invalid_otp")
            raise VerificationError("Invalid or expired verification OTP", field="otp")
        if user.phone_number_verified:
            await logger.awarning(
                "phone_number_verification_failed",
                reason="already_verified",
                user_id=str(user.id),
            )
            raise VerificationError("This phone number is already verified", field="otp")
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
        try:
            await self._audit.record(
                action=AuditAction.VERIFY_PHONE,
                actor_id=user.id,
                entity_type="user",
                entity_id=str(user.id),
            )
        except Exception:
            await logger.awarning("audit_write_failed", action=AuditAction.VERIFY_PHONE)
