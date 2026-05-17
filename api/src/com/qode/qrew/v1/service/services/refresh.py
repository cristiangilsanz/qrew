import uuid

import jwt
import redis.asyncio as aioredis
import structlog
from jwt import ExpiredSignatureError, InvalidTokenError

from com.qode.qrew.v1.service.core.errors import DomainError
from com.qode.qrew.v1.service.core.security import create_access_token
from com.qode.qrew.v1.service.repositories.user import UserRepository
from com.qode.qrew.v1.service.schemas.auth import RefreshRequest, RefreshResponse
from com.qode.qrew.v1.service.services.logout import JTI_BLACKLIST_PREFIX
from com.qode.qrew.v1.service.settings import settings

logger = structlog.get_logger(__name__)


class RefreshError(DomainError):
    """A business-rule violation raised when a token refresh cannot be completed."""


class RefreshService:
    def __init__(self, repo: UserRepository, redis: aioredis.Redis) -> None:  # type: ignore[type-arg]
        self._repo = repo
        self._redis = redis

    async def refresh(self, request: RefreshRequest) -> RefreshResponse:
        """Issue a new access token from a valid refresh token."""
        try:
            payload = jwt.decode(
                request.refresh_token,
                settings.secret_key,
                algorithms=["HS256"],
            )
        except ExpiredSignatureError as exc:
            await logger.awarning("refresh_failed", reason="token_expired")
            raise RefreshError("Refresh token has expired") from exc
        except InvalidTokenError as exc:
            await logger.awarning("refresh_failed", reason="invalid_token")
            raise RefreshError("Invalid refresh token") from exc

        if payload.get("type") != "refresh":
            await logger.awarning("refresh_failed", reason="wrong_token_type")
            raise RefreshError("Invalid token type")

        jti = payload.get("jti")
        key = JTI_BLACKLIST_PREFIX + jti if isinstance(jti, str) else None
        if key and await self._redis.exists(key):
            await logger.awarning("refresh_failed", reason="token_revoked")
            raise RefreshError("Refresh token has been revoked")

        subject = payload.get("sub")
        if not isinstance(subject, str):
            await logger.awarning("refresh_failed", reason="invalid_subject")
            raise RefreshError("Invalid refresh token")

        try:
            user_id = uuid.UUID(subject)
        except ValueError as exc:
            await logger.awarning("refresh_failed", reason="invalid_subject")
            raise RefreshError("Invalid refresh token") from exc

        user = await self._repo.get_by_id(user_id)
        if user is None or not user.is_active:
            await logger.awarning("refresh_failed", reason="user_not_found_or_inactive")
            raise RefreshError("Invalid refresh token")

        access_token = create_access_token(str(user.id))
        await logger.ainfo("token_refreshed", user_id=str(user.id))

        return RefreshResponse(access_token=access_token)
