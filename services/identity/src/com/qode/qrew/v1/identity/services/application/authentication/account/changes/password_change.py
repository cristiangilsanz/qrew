import redis.asyncio as aioredis
import structlog

from com.qode.qrew.v1.identity.services.application.authentication.token.security import (
    hash_password,
    is_password_pwned,
    verify_password,
)
from com.qode.qrew.v1.identity.core.errors import DomainError
from com.qode.qrew.v1.identity.models.audit import AuditAction
from com.qode.qrew.v1.identity.models.user import User
from com.qode.qrew.v1.identity.repositories.session import SessionRepository
from com.qode.qrew.v1.identity.repositories.user import UserRepository
from com.qode.qrew.v1.identity.services.application.audit import AuditService
from com.qode.qrew.v1.identity.services.application.authentication.login.flow.logout import (
    BLACKLIST_JTI_PREFIX,
)
from com.qode.qrew.v1.identity.core.config import settings

logger = structlog.get_logger(__name__)


class PasswordChangeError(DomainError):
    """Raised when a password change cannot be completed."""


class PasswordChangeService:
    def __init__(
        self,
        user_repo: UserRepository,
        session_repo: SessionRepository,
        redis: aioredis.Redis,  # type: ignore[type-arg]
        audit: AuditService,
    ) -> None:
        self._user_repo = user_repo
        self._session_repo = session_repo
        self._redis = redis
        self._audit = audit

    async def change_password(self, user: User, current_password: str, new_password: str) -> None:
        """Verify current password, update to new one, and revoke all sessions."""
        if not verify_password(current_password, user.hashed_password):
            raise PasswordChangeError("Current password is incorrect", field="current_password")

        if await is_password_pwned(new_password):
            raise PasswordChangeError(
                "This password has appeared in a known data breach. Choose a different one",
                field="new_password",
            )

        user.hashed_password = hash_password(new_password)
        await self._user_repo.save(user)

        jtis = await self._session_repo.delete_all_by_user_id(user.id)
        ttl = settings.refresh_token_expire_days * 24 * 3600
        for jti in jtis:
            await self._redis.setex(BLACKLIST_JTI_PREFIX + jti, ttl, "revoked")

        await logger.ainfo("password_changed", user_id=str(user.id))
        try:
            await self._audit.record(
                action=AuditAction.PASSWORD_CHANGED,
                actor_id=user.id,
                entity_type="user",
                entity_id=str(user.id),
            )
        except Exception as exc:
            await logger.awarning(
                "audit_write_failed", action=AuditAction.PASSWORD_CHANGED, error=repr(exc)
            )
