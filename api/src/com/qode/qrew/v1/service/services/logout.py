import uuid
from datetime import UTC, datetime

import redis.asyncio as aioredis
import structlog
from jwt import ExpiredSignatureError, InvalidTokenError

from com.qode.qrew.v1.service.core.errors import DomainError
from com.qode.qrew.v1.service.core.security import decode_refresh_token
from com.qode.qrew.v1.service.models.audit import AuditAction
from com.qode.qrew.v1.service.services.audit import AuditService

logger = structlog.get_logger(__name__)

JTI_BLACKLIST_PREFIX = "blacklist:jti:"


class LogoutError(DomainError):
    """A business-rule violation raised when logout cannot be completed."""


class LogoutService:
    def __init__(self, redis: aioredis.Redis, audit: AuditService) -> None:  # type: ignore[type-arg]
        self._redis = redis
        self._audit = audit

    async def logout(self, refresh_token: str) -> None:
        """Blacklist the refresh token's JTI so it cannot be used again."""
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
        ttl = (
            int(exp) - int(datetime.now(UTC).timestamp())
            if isinstance(exp, (int, float))
            else 0
        )

        if ttl > 0:
            await self._redis.setex(JTI_BLACKLIST_PREFIX + jti, ttl, "1")

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
