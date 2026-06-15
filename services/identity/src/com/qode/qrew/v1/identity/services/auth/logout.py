import uuid
from datetime import UTC, datetime

import redis.asyncio as aioredis
import structlog
from jwt import ExpiredSignatureError, InvalidTokenError

from com.qode.qrew.v1.identity.services.auth.security import decode_refresh_token
from com.qode.qrew.v1.identity.core.errors import DomainError
from com.qode.qrew.v1.identity.models.audit.audit import AuditAction
from com.qode.qrew.v1.identity.repositories.auth.session import SessionRepository
from com.qode.qrew.v1.identity.services.audit import AuditService

logger = structlog.get_logger(__name__)

BLACKLIST_JTI_PREFIX = "blacklist:jti:"
BLACKLIST_USER_PREFIX = "blacklist:user:"


class LogoutError(DomainError):
    """A business-rule violation raised when logout cannot be completed."""


class LogoutService:
    def __init__(
        self,
        redis: aioredis.Redis,  # type: ignore[type-arg]
        audit: AuditService,
        session_repo: SessionRepository | None = None,
    ) -> None:
        self._redis = redis
        self._audit = audit
        self._session_repo = session_repo

    async def logout(self, refresh_token: str) -> None:
        """Revokes a refresh token and removes the associated session record."""
        try:
            payload = decode_refresh_token(refresh_token)
        except ExpiredSignatureError:
            return
        except InvalidTokenError as exc:
            raise LogoutError("Invalid refresh token") from exc

        if payload.get("type") != "refresh":
            raise LogoutError("Invalid token type")

        jti = payload.get("jti")
        if not isinstance(jti, str):
            raise LogoutError("Invalid refresh token")

        exp = payload.get("exp")
        ttl = int(exp) - int(datetime.now(UTC).timestamp()) if isinstance(exp, (int, float)) else 0

        if ttl > 0:
            await self._redis.setex(BLACKLIST_JTI_PREFIX + jti, ttl, "1")

        if self._session_repo is not None:
            await self._session_repo.delete_by_jti(jti)

        await logger.ainfo("token_revoked", jti=jti)

        sub = payload.get("sub")
        try:
            actor_id = uuid.UUID(sub) if isinstance(sub, str) else None
            await self._audit.record(
                action=AuditAction.LOGOUT,
                actor_id=actor_id,
                entity_type="user",
                entity_id=sub if isinstance(sub, str) else None,
                payload={"jti": jti},
            )
        except Exception:
            await logger.awarning("audit_write_failed", action=AuditAction.LOGOUT)
