from dataclasses import dataclass

import redis.asyncio as aioredis
from fastapi import WebSocket
from jwt import ExpiredSignatureError, InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.identity.core.auth import jwt_keys
from com.qode.qrew.v1.identity.models.auth.session import Session
from com.qode.qrew.v1.identity.models.auth.user import User
from com.qode.qrew.v1.identity.repositories.auth.session import SessionRepository
from com.qode.qrew.v1.identity.repositories.auth.user import UserRepository

_PROTOCOL_PREFIX = "bearer."


class WebSocketAuthError(Exception):
    """Raised when a WebSocket handshake cannot be authenticated."""


@dataclass(frozen=True)
class WebSocketIdentity:
    user: User
    session: Session
    accepted_subprotocol: str | None


def extract_token(websocket: WebSocket) -> tuple[str, str | None] | None:
    """Pull a bearer token from the subprotocol header or the query string."""
    raw = websocket.headers.get("sec-websocket-protocol")
    if raw:
        for entry in raw.split(","):
            value = entry.strip()
            if value.startswith(_PROTOCOL_PREFIX):
                token = value[len(_PROTOCOL_PREFIX) :]
                if token:
                    return token, value
    token = websocket.query_params.get("token")
    if token:
        return token, None
    return None


async def authenticate(
    websocket: WebSocket,
    db: AsyncSession,
    redis_client: aioredis.Redis,  # type: ignore[type-arg]
) -> WebSocketIdentity:
    """Validate the handshake and return the authenticated user and session."""
    extracted = extract_token(websocket)
    if extracted is None:
        raise WebSocketAuthError("missing token")
    token, protocol_value = extracted

    try:
        payload = jwt_keys.verify(jwt_keys.ACCESS, token)
    except (ExpiredSignatureError, InvalidTokenError) as exc:
        raise WebSocketAuthError("invalid token") from exc

    if payload.get("type") != "access" or payload.get("scope") != "access":
        raise WebSocketAuthError("invalid token type")

    jti = payload.get("jti")
    if not isinstance(jti, str):
        raise WebSocketAuthError("invalid token claims")

    if await redis_client.get(f"blacklist:jti:{jti}") is not None:  # type: ignore[misc]
        raise WebSocketAuthError("session revoked")

    session = await SessionRepository(db).get_by_jti(jti)
    if session is None:
        raise WebSocketAuthError("session not found")

    user = await UserRepository(db).get_by_id(session.user_id)
    if user is None or not user.is_active:
        raise WebSocketAuthError("user inactive")

    return WebSocketIdentity(user=user, session=session, accepted_subprotocol=protocol_value)
