# requests and confirms a change of a user's email address
from datetime import UTC, datetime, timedelta

import structlog

from com.qode.qrew.v1.identity.core.utils import pii as pii_crypto
from com.qode.qrew.v1.identity.services.application.authentication.token.security import (
    generate_token,
    verify_password,
)
from com.qode.qrew.v1.identity.core.errors import DomainError
from com.qode.qrew.v1.identity.models.audit import AuditAction
from com.qode.qrew.v1.identity.models.user import User
from com.qode.qrew.v1.identity.repositories.user import UserRepository
from com.qode.qrew.v1.identity.services.application.audit import AuditService
from com.qode.qrew.v1.identity.services.application.notification.dispatcher import (
    NotificationDispatcher,
)
from com.qode.qrew.v1.identity.core.config import settings

logger = structlog.get_logger(__name__)


class EmailChangeError(DomainError):
    pass


class EmailChangeService:
    # stores the repository notifier and audit service the service uses
    def __init__(
        self,
        user_repo: UserRepository,
        notifier: NotificationDispatcher,
        audit: AuditService,
    ) -> None:
        self._user_repo = user_repo
        self._notifier = notifier
        self._audit = audit

    # verifies the password and sends a confirmation link to the new email
    async def request_change(self, user: User, new_email: str, current_password: str) -> None:
        if not verify_password(current_password, user.hashed_password):
            raise EmailChangeError("Current password rejected.", field="current_password")

        if new_email == user.email:
            raise EmailChangeError(
                "New email must be different from the current one", field="new_email"
            )

        if await self._user_repo.exists_by_email(new_email):
            raise EmailChangeError("Email already taken.", field="new_email")

        token = generate_token()
        expires_at = datetime.now(UTC) + timedelta(
            hours=settings.email_verification_token_expire_hours
        )
        user.pending_email = new_email
        user.pending_email_verification_token = pii_crypto.hash_lookup(token)
        user.pending_email_token_expires_at = expires_at
        await self._user_repo.save(user)

        await self._notifier.send_email_change_verification(new_email, user.full_name, token)
        await self._notifier.send_email_change_alert(user.email, user.full_name, new_email)

        await logger.ainfo("email_change_requested", user_id=str(user.id))
        try:
            await self._audit.record(
                action=AuditAction.EMAIL_CHANGE_REQUESTED,
                actor_id=user.id,
                entity_type="user",
                entity_id=str(user.id),
            )
        except Exception as exc:
            await logger.awarning(
                "audit_write_failed", action=AuditAction.EMAIL_CHANGE_REQUESTED, error=repr(exc)
            )

    # confirms a pending email change using its verification token
    async def confirm_change(self, token: str) -> None:
        user = await self._user_repo.get_by_pending_email_token(token)
        if user is None or user.pending_email is None:
            raise EmailChangeError("Token expired.", field="token")

        if (
            user.pending_email_token_expires_at is None
            or user.pending_email_token_expires_at < datetime.now(UTC)
        ):
            raise EmailChangeError("Token expired.", field="token")

        new_email = user.pending_email

        if await self._user_repo.exists_by_email(new_email):
            raise EmailChangeError("Email already taken.", field="token")

        user.email = new_email
        user.pending_email = None
        user.pending_email_verification_token = None
        user.pending_email_token_expires_at = None
        await self._user_repo.save(user)

        await logger.ainfo("email_change_confirmed", user_id=str(user.id))
        try:
            await self._audit.record(
                action=AuditAction.EMAIL_CHANGE_CONFIRMED,
                actor_id=user.id,
                entity_type="user",
                entity_id=str(user.id),
                payload={"new_email": new_email},
            )
        except Exception as exc:
            await logger.awarning(
                "audit_write_failed", action=AuditAction.EMAIL_CHANGE_CONFIRMED, error=repr(exc)
            )
