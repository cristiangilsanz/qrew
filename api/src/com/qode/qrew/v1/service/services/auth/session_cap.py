import uuid

import redis.asyncio as aioredis
import structlog

from com.qode.qrew.v1.service.models.audit.audit import AuditAction
from com.qode.qrew.v1.service.repositories.auth.session import SessionRepository
from com.qode.qrew.v1.service.services.audit import AuditService
from com.qode.qrew.v1.service.services.auth.logout import BLACKLIST_JTI_PREFIX
from com.qode.qrew.v1.service.settings import settings

logger = structlog.get_logger(__name__)


class SessionCapEnforcer:
    """Evict the oldest sessions when the per-user session cap is exceeded."""

    def __init__(
        self,
        session_repo: SessionRepository,
        audit: AuditService,
        redis: aioredis.Redis | None = None,  # type: ignore[type-arg]
    ) -> None:
        self._session_repo = session_repo
        self._audit = audit
        self._redis = redis

    async def enforce(self, user_id: uuid.UUID) -> None:
        """Evict the oldest sessions if the user is over the configured cap."""
        cap = settings.max_sessions_per_user
        if cap <= 0:
            return
        count = await self._session_repo.count_by_user_id(user_id)
        if count <= cap:
            return
        overflow = count - cap
        victims = await self._session_repo.get_oldest_by_user_id(user_id, overflow)
        ttl = settings.refresh_token_expire_days * 86400
        for victim in victims:
            jti = victim.jti
            await self._session_repo.delete_by_jti(jti)
            if self._redis is not None:
                await self._redis.setex(BLACKLIST_JTI_PREFIX + jti, ttl, "1")
            await logger.ainfo("session_evicted", user_id=str(user_id), jti=jti)
            await self._audit_safe(user_id, victim.id, jti)

    async def _audit_safe(
        self, user_id: uuid.UUID, session_id: uuid.UUID, jti: str
    ) -> None:
        """Record a session-cap eviction audit event without raising."""
        try:
            await self._audit.record(
                action=AuditAction.SESSION_EVICTED,
                actor_id=user_id,
                entity_type="session",
                entity_id=str(session_id),
                payload={"reason": "session_cap", "jti": jti},
            )
        except Exception:
            await logger.awarning(
                "audit_write_failed", action=AuditAction.SESSION_EVICTED
            )
