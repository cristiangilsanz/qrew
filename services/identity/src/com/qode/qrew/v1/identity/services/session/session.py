import uuid

import redis.asyncio as aioredis
import structlog

from com.qode.qrew.v1.identity.core.infra.errors import DomainError
from com.qode.qrew.v1.identity.repositories.auth.session import SessionRepository
from com.qode.qrew.v1.identity.schemas.auth.session import SessionResponse
from com.qode.qrew.v1.identity.services.auth.logout import BLACKLIST_JTI_PREFIX
from com.qode.qrew.v1.identity.settings import settings

logger = structlog.get_logger(__name__)


class SessionError(DomainError):
    """Raised when a session operation cannot be completed."""


class SessionService:
    def __init__(
        self,
        repo: SessionRepository,
        redis: aioredis.Redis,  # type: ignore[type-arg]
    ) -> None:
        self._repo = repo
        self._redis = redis

    async def list_sessions(self, user_id: uuid.UUID) -> list[SessionResponse]:
        """Return all active sessions for the given user."""
        sessions = await self._repo.get_all_by_user_id(user_id)
        return [
            SessionResponse(
                id=str(s.id),
                jti=s.jti,
                ip_address=s.ip_address,
                user_agent=s.user_agent,
                device_fingerprint=s.device_fingerprint,
                created_at=s.created_at,
                last_used_at=s.last_used_at,
            )
            for s in sessions
        ]

    async def revoke_session(self, jti: str, user_id: uuid.UUID) -> None:
        """Blacklist a specific session JTI and delete its row."""
        session = await self._repo.get_by_jti(jti)
        if session is None or session.user_id != user_id:
            raise SessionError("Session not found", field="jti")

        await self._blacklist_jti(jti)
        await self._repo.delete_by_jti(jti)
        await logger.ainfo("session_revoked", jti=jti, user_id=str(user_id))

    async def revoke_all(self, user_id: uuid.UUID) -> None:
        """Blacklist and delete every session for the given user."""
        jtis = await self._repo.delete_all_by_user_id(user_id)
        for jti in jtis:
            await self._blacklist_jti(jti)
        await logger.ainfo("sessions_revoked_all", count=len(jtis), user_id=str(user_id))

    async def _blacklist_jti(self, jti: str) -> None:
        ttl = settings.refresh_token_expire_days * 24 * 3600
        await self._redis.setex(BLACKLIST_JTI_PREFIX + jti, ttl, "revoked")
