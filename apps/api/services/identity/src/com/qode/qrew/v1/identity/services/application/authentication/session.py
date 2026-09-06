# lists and revokes a user's login sessions
import uuid

import redis.asyncio as aioredis
import structlog

from com.qode.qrew.v1.identity.core.errors import DomainError
from com.qode.qrew.v1.identity.core.utils.geoip import GeoIpService
from com.qode.qrew.v1.identity.repositories.session import SessionRepository
from com.qode.qrew.v1.identity.schemas.authentication.session import SessionResponse
from com.qode.qrew.v1.identity.services.application.authentication.login.flow.logout import (
    BLACKLIST_JTI_PREFIX,
)
from com.qode.qrew.v1.identity.core.config import settings

logger = structlog.get_logger(__name__)


class SessionError(DomainError):
    pass


class SessionService:
    # stores the repository redis client and geoip service the service uses
    def __init__(
        self,
        repo: SessionRepository,
        redis: aioredis.Redis,  # type: ignore[type-arg]
        geoip: GeoIpService,
    ) -> None:
        self._repo = repo
        self._redis = redis
        self._geoip = geoip

    # lists a user's sessions with their approximate location
    async def list_sessions(
        self, user_id: uuid.UUID, current_jti: str | None = None
    ) -> list[SessionResponse]:
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
                is_current=s.jti == current_jti,
                location=self._geoip.locate_label(s.ip_address) if s.ip_address else None,
            )
            for s in sessions
        ]

    # revokes one of a user's sessions
    async def revoke_session(self, jti: str, user_id: uuid.UUID) -> None:
        session = await self._repo.get_by_jti(jti)
        if session is None or session.user_id != user_id:
            raise SessionError("Session not found.", field="jti")

        await self._blacklist_jti(jti)
        await self._repo.delete_by_jti(jti)
        await logger.ainfo("session_revoked", jti=jti, user_id=str(user_id))

    # revokes every session of a user
    async def revoke_all(self, user_id: uuid.UUID) -> None:
        jtis = await self._repo.delete_all_by_user_id(user_id)
        for jti in jtis:
            await self._blacklist_jti(jti)
        await logger.ainfo("sessions_revoked_all", count=len(jtis), user_id=str(user_id))

    # blacklists a refresh token identifier for the rest of its lifetime
    async def _blacklist_jti(self, jti: str) -> None:
        ttl = settings.refresh_token_expire_days * 24 * 3600
        await self._redis.setex(BLACKLIST_JTI_PREFIX + jti, ttl, "revoked")
