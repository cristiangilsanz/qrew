import uuid
from typing import Annotated

import redis.asyncio as aioredis
import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import ExpiredSignatureError, InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.identity.services.auth import jwt_keys
from com.qode.qrew.v1.identity.database import get_db
from com.qode.qrew.v1.identity.redis import get_redis
from com.qode.qrew.v1.identity.models.auth.session import Session
from com.qode.qrew.v1.identity.models.auth.user import User
from com.qode.qrew.v1.identity.repositories.auth.session import SessionRepository
from com.qode.qrew.v1.identity.repositories.auth.user import UserRepository

logger = structlog.get_logger(__name__)

_bearer = HTTPBearer()

_CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail={"message": "Invalid or expired token", "field": None},
)

_SETUP_REQUIRED_EXCEPTION = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail={
        "message": "Setup not complete. Use /auth/complete-setup first.",
        "field": None,
    },
)


async def _resolve_user(
    credentials: HTTPAuthorizationCredentials,
    db: AsyncSession,
    *,
    allow_setup: bool,
) -> User:
    try:
        matched, payload = jwt_keys.verify_any(
            (jwt_keys.ACCESS, jwt_keys.SETUP), credentials.credentials
        )
    except (ExpiredSignatureError, InvalidTokenError) as exc:
        raise _CREDENTIALS_EXCEPTION from exc

    if payload.get("type") != "access":
        raise _CREDENTIALS_EXCEPTION

    if matched == jwt_keys.SETUP and not allow_setup:
        raise _SETUP_REQUIRED_EXCEPTION

    subject = payload.get("sub")
    if not isinstance(subject, str):
        raise _CREDENTIALS_EXCEPTION

    try:
        user_id = uuid.UUID(subject)
    except ValueError as exc:
        raise _CREDENTIALS_EXCEPTION from exc

    user = await UserRepository(db).get_by_id(user_id)
    if user is None or not user.is_active:
        raise _CREDENTIALS_EXCEPTION

    return user


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    db: AsyncSession = Depends(get_db),
) -> User:
    """Resolve the authenticated user from a full access token."""
    return await _resolve_user(credentials, db, allow_setup=False)


async def get_setup_or_full_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    db: AsyncSession = Depends(get_db),
) -> User:
    """Resolve the authenticated user from a setup or full access token."""
    return await _resolve_user(credentials, db, allow_setup=True)


async def get_recovery_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    db: AsyncSession = Depends(get_db),
) -> User:
    """Resolve the authenticated user from a recovery token."""
    try:
        payload = jwt_keys.verify(jwt_keys.RECOVERY, credentials.credentials)
    except (ExpiredSignatureError, InvalidTokenError) as exc:
        raise _CREDENTIALS_EXCEPTION from exc

    if payload.get("type") != "access" or payload.get("scope") != "recovery":
        raise _CREDENTIALS_EXCEPTION

    subject = payload.get("sub")
    if not isinstance(subject, str):
        raise _CREDENTIALS_EXCEPTION

    try:
        user_id = uuid.UUID(subject)
    except ValueError as exc:
        raise _CREDENTIALS_EXCEPTION from exc

    user = await UserRepository(db).get_by_id(user_id)
    if user is None or not user.is_active:
        raise _CREDENTIALS_EXCEPTION

    return user


async def get_current_session(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    db: AsyncSession = Depends(get_db),
    redis: Annotated[aioredis.Redis, Depends(get_redis)] = ...,  # type: ignore[type-arg, assignment]
) -> Session:
    """Resolve the session associated with the current access token."""
    try:
        payload = jwt_keys.verify(jwt_keys.ACCESS, credentials.credentials)
    except (ExpiredSignatureError, InvalidTokenError) as exc:
        raise _CREDENTIALS_EXCEPTION from exc

    if payload.get("type") != "access" or payload.get("scope") != "access":
        raise _CREDENTIALS_EXCEPTION

    jti = payload.get("jti")
    if not isinstance(jti, str):
        raise _CREDENTIALS_EXCEPTION

    if await redis.get(f"blacklist:jti:{jti}") is not None:
        raise _CREDENTIALS_EXCEPTION

    session = await SessionRepository(db).get_by_jti(jti)
    if session is None:
        raise _CREDENTIALS_EXCEPTION

    return session


async def get_admin_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Require the authenticated user to be an administrator."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": "Admin access required", "field": None},
        )
    return current_user
