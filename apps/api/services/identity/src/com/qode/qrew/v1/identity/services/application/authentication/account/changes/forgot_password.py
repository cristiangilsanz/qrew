from datetime import UTC, datetime, timedelta

import structlog

from com.qode.qrew.v1.identity.services.application.authentication.token.security import (
    generate_token,
    hash_password,
)
from com.qode.qrew.v1.identity.core.errors import DomainError
from com.qode.qrew.v1.identity.repositories.user import UserRepository
from com.qode.qrew.v1.identity.services.application.notification.dispatcher import (
    NotificationDispatcher,
)
from com.qode.qrew.v1.identity.core.config import settings

logger = structlog.get_logger(__name__)


class ForgotPasswordError(DomainError):
    """Raised when a password reset cannot be completed."""


class ForgotPasswordService:
    def __init__(
        self,
        user_repo: UserRepository,
        notifier: NotificationDispatcher,
    ) -> None:
        self._user_repo = user_repo
        self._notifier = notifier

    async def request_reset(self, email: str) -> None:
        """Generate a reset token and email it; always succeeds silently for unknown emails."""
        user = await self._user_repo.get_by_email(email)
        if user is None or not user.is_active:
            return

        token = generate_token()
        expires_at = datetime.now(UTC) + timedelta(
            hours=settings.email_verification_token_expire_hours
        )
        user.password_reset_token = token
        user.password_reset_token_expires_at = expires_at
        await self._user_repo.save(user)

        try:
            await self._notifier.send_forgot_password(user.email, user.full_name, token)
        except Exception as exc:
            await logger.awarning("notification_failed", action="forgot_password", error=repr(exc))

    async def reset_password(self, token: str, new_password: str) -> None:
        """Verify the token and update the user's password."""
        user = await self._user_repo.get_by_password_reset_token(token)
        if user is None or user.password_reset_token != token:
            raise ForgotPasswordError("Invalid or expired reset link.", field="token")

        if (
            user.password_reset_token_expires_at is None
            or user.password_reset_token_expires_at < datetime.now(UTC)
        ):
            raise ForgotPasswordError("Invalid or expired reset link.", field="token")

        user.hashed_password = hash_password(new_password)
        user.password_reset_token = None
        user.password_reset_token_expires_at = None
        await self._user_repo.save(user)
        await logger.ainfo("password_reset_complete", user_id=str(user.id))
