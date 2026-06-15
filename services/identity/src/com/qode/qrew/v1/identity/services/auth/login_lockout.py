import uuid

import redis.asyncio as aioredis
import structlog

from com.qode.qrew.v1.identity.core.errors import DomainError
from com.qode.qrew.v1.identity.models.audit.audit import AuditAction
from com.qode.qrew.v1.identity.services.audit import AuditService
from com.qode.qrew.v1.identity.core.config import settings

logger = structlog.get_logger(__name__)

_FAILED_PREFIX = "login:failed:"
_LOCK_PREFIX = "login:lock:"


def _backoff_schedule() -> list[tuple[int, int]]:
    base = settings.login_lockout_base_seconds
    return [
        (settings.login_max_attempts, base),
        (settings.login_max_attempts * 2, base * 6),
        (settings.login_max_attempts * 4, base * 288),
    ]


class LoginLockoutError(DomainError):
    """Raised when an account is currently locked out."""

    def __init__(self, message: str, retry_after_seconds: int) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


def _failed_key(user_id: uuid.UUID) -> str:
    return f"{_FAILED_PREFIX}{user_id}"


def _lock_key(user_id: uuid.UUID) -> str:
    return f"{_LOCK_PREFIX}{user_id}"


class LoginLockoutService:
    def __init__(
        self,
        redis: aioredis.Redis,  # type: ignore[type-arg]
        audit: AuditService,
    ) -> None:
        self._redis = redis
        self._audit = audit

    async def check_not_locked(self, user_id: uuid.UUID) -> None:
        """Raises an error if the account is currently locked out."""
        ttl: int = await self._redis.ttl(_lock_key(user_id))
        if ttl > 0:
            raise LoginLockoutError(
                "Account temporarily locked due to too many failed login attempts",
                retry_after_seconds=ttl,
            )

    async def record_failure(
        self,
        user_id: uuid.UUID,
        ip_address: str | None = None,
    ) -> None:
        """Increment the failure counter and trigger a lockout if a threshold is hit."""
        key = _failed_key(user_id)
        attempts: int = await self._redis.incr(key)
        if attempts == 1:
            longest = _backoff_schedule()[-1][1]
            await self._redis.expire(key, longest * 2)

        duration = self._duration_for_attempts(attempts)
        if duration is None:
            return

        await self._redis.setex(_lock_key(user_id), duration, "1")
        await logger.awarning(
            "login_locked",
            user_id=str(user_id),
            attempts=attempts,
            duration_seconds=duration,
        )
        try:
            await self._audit.record(
                action=AuditAction.LOGIN_LOCKED,
                actor_id=user_id,
                entity_type="user",
                entity_id=str(user_id),
                ip_address=ip_address,
                payload={"attempts": attempts, "duration_seconds": duration},
            )
        except Exception:
            await logger.awarning("audit_write_failed", action=AuditAction.LOGIN_LOCKED)

    async def reset(self, user_id: uuid.UUID) -> None:
        """Clear the failure counter and any active lock."""
        await self._redis.delete(_failed_key(user_id), _lock_key(user_id))

    async def admin_unlock(self, user_id: uuid.UUID, admin_id: uuid.UUID) -> None:
        """Admin-triggered unlock: clears the lock and records an audit event."""
        await self.reset(user_id)
        try:
            await self._audit.record(
                action=AuditAction.LOGIN_UNLOCKED,
                actor_id=admin_id,
                entity_type="user",
                entity_id=str(user_id),
            )
        except Exception:
            await logger.awarning("audit_write_failed", action=AuditAction.LOGIN_UNLOCKED)

    @staticmethod
    def _duration_for_attempts(attempts: int) -> int | None:
        """Returns the lockout duration in seconds for the given attempt count, or nothing if no threshold is matched."""
        match: int | None = None
        for threshold, duration in _backoff_schedule():
            if attempts == threshold:
                match = duration
        return match
