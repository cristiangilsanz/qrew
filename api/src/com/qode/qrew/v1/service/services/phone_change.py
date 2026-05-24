from datetime import UTC, datetime

import structlog

from com.qode.qrew.v1.service.core.errors import DomainError
from com.qode.qrew.v1.service.core.security import (
    generate_otp,
    phone_number_otp_expiry,
    verify_password,
)
from com.qode.qrew.v1.service.models.audit import AuditAction
from com.qode.qrew.v1.service.models.user import User
from com.qode.qrew.v1.service.repositories.user import UserRepository
from com.qode.qrew.v1.service.services.audit import AuditService
from com.qode.qrew.v1.service.services.notification import NotificationDispatcher

logger = structlog.get_logger(__name__)


class PhoneChangeError(DomainError):
    """Raised when a phone number change cannot be completed."""


class PhoneChangeService:
    def __init__(
        self,
        user_repo: UserRepository,
        notifier: NotificationDispatcher,
        audit: AuditService,
    ) -> None:
        self._user_repo = user_repo
        self._notifier = notifier
        self._audit = audit

    async def request_change(
        self, user: User, new_phone_number: str, current_password: str
    ) -> None:
        """Verify password, store pending phone state, and send OTP to new number."""
        if not verify_password(current_password, user.hashed_password):
            raise PhoneChangeError(
                "Current password is incorrect", field="current_password"
            )

        if new_phone_number == user.phone_number:
            raise PhoneChangeError(
                "New phone number must be different from the current one",
                field="new_phone_number",
            )

        if await self._user_repo.exists_by_phone(new_phone_number):
            raise PhoneChangeError(
                "Phone number already in use", field="new_phone_number"
            )

        otp = generate_otp()
        user.pending_phone_number = new_phone_number
        user.pending_phone_otp = otp
        user.pending_phone_otp_expires_at = phone_number_otp_expiry()
        await self._user_repo.save(user)

        await self._notifier.send_sms_otp(new_phone_number, otp)

        await logger.ainfo("phone_change_requested", user_id=str(user.id))
        try:
            await self._audit.record(
                action=AuditAction.PHONE_CHANGE_REQUESTED,
                actor_id=user.id,
                entity_type="user",
                entity_id=str(user.id),
            )
        except Exception:
            await logger.awarning(
                "audit_write_failed", action=AuditAction.PHONE_CHANGE_REQUESTED
            )

    async def confirm_change(self, user: User, new_phone_number: str, otp: str) -> None:
        """Validate OTP and swap the phone number."""
        if (
            user.pending_phone_number != new_phone_number
            or user.pending_phone_otp != otp
        ):
            raise PhoneChangeError("Invalid or expired verification code", field="otp")

        if (
            user.pending_phone_otp_expires_at is None
            or user.pending_phone_otp_expires_at < datetime.now(UTC)
        ):
            raise PhoneChangeError("Invalid or expired verification code", field="otp")

        if await self._user_repo.exists_by_phone(new_phone_number):
            raise PhoneChangeError(
                "This phone number is no longer available", field="new_phone_number"
            )

        user.phone_number = new_phone_number
        user.pending_phone_number = None
        user.pending_phone_otp = None
        user.pending_phone_otp_expires_at = None
        await self._user_repo.save(user)

        await logger.ainfo("phone_change_confirmed", user_id=str(user.id))
        try:
            await self._audit.record(
                action=AuditAction.PHONE_CHANGE_CONFIRMED,
                actor_id=user.id,
                entity_type="user",
                entity_id=str(user.id),
                payload={"new_phone_number": new_phone_number},
            )
        except Exception:
            await logger.awarning(
                "audit_write_failed", action=AuditAction.PHONE_CHANGE_CONFIRMED
            )
