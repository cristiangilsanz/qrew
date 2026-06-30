import functools
from dataclasses import dataclass

import jwt
from cryptography.hazmat.primitives import serialization
from fastapi import WebSocket

from com.qode.qrew.v1.gateway.core.config import settings

ALGORITHM = "ES256"

_PROTOCOL_PREFIX = "bearer."


class WebSocketAuthError(Exception):
    pass


@dataclass(frozen=True)
class WebSocketIdentity:
    claims: dict[str, object]
    accepted_subprotocol: str | None


def _load_public_pem(private_pem: str) -> str:
    key = serialization.load_pem_private_key(private_pem.encode(), password=None)
    return (
        key.public_key()  # type: ignore[union-attr]
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )


@functools.cache
def _access_public_keys() -> list[str]:
    """Derived once from settings; cached for the lifetime of the process."""
    keys: list[str] = []
    if settings.access_jwt_private_key:
        keys.append(_load_public_pem(settings.access_jwt_private_key))
    for entry in settings.access_jwt_previous_public_keys.split(","):
        pem = entry.strip()
        if pem:
            keys.append(pem)
    return keys


@functools.cache
def _scanner_public_keys() -> list[str]:
    """Derived once from settings; cached for the lifetime of the process."""
    if settings.scanner_jwt_private_key:
        return [_load_public_pem(settings.scanner_jwt_private_key)]
    return []


def _extract_token(websocket: WebSocket) -> tuple[str, str | None] | None:
    raw = websocket.headers.get("sec-websocket-protocol")
    if raw:
        for entry in raw.split(","):
            value = entry.strip()
            if value.startswith(_PROTOCOL_PREFIX):
                token = value[len(_PROTOCOL_PREFIX) :]
                if token:
                    return token, value
    return None


def _try_verify(token: str, public_keys: list[str]) -> dict[str, object] | None:
    audience = settings.jwt_audience or None
    issuer = settings.jwt_issuer or None
    for public_pem in public_keys:
        try:
            return jwt.decode(  # type: ignore[return-value]
                token,
                public_pem,
                algorithms=[ALGORITHM],
                audience=audience,
                issuer=issuer,
            )
        except jwt.InvalidTokenError:
            continue
    return None


def authenticate(websocket: WebSocket) -> WebSocketIdentity:
    extracted = _extract_token(websocket)
    if extracted is None:
        raise WebSocketAuthError("missing token")
    token, protocol_value = extracted

    claims = _try_verify(token, _access_public_keys())
    if claims is not None:
        if claims.get("type") != "access":
            raise WebSocketAuthError("invalid token type")
        return WebSocketIdentity(claims=claims, accepted_subprotocol=protocol_value)

    scanner_keys = _scanner_public_keys()
    if scanner_keys:
        claims = _try_verify(token, scanner_keys)
        if claims is not None and claims.get("type") == "scanner":
            return WebSocketIdentity(claims=claims, accepted_subprotocol=protocol_value)

    raise WebSocketAuthError("invalid token")
