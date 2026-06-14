"""Verifies JWT credentials for incoming WebSocket connections without database access."""

from dataclasses import dataclass

import jwt
from cryptography.hazmat.primitives import serialization
from fastapi import WebSocket

from com.qode.qrew.v1.gateway.settings import settings

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


def _access_public_keys() -> list[str]:
    keys: list[str] = []
    if settings.access_jwt_private_key:
        keys.append(_load_public_pem(settings.access_jwt_private_key))
    for entry in settings.access_jwt_previous_public_keys.split(","):
        pem = entry.strip()
        if pem:
            keys.append(pem)
    return keys or [""]


def _scanner_public_keys() -> list[str]:
    if settings.scanner_jwt_private_key:
        return [_load_public_pem(settings.scanner_jwt_private_key)]
    return []


def _extract_token(websocket: WebSocket) -> tuple[str, str | None] | None:
    raw = websocket.headers.get("sec-websocket-protocol")
    if raw:
        for entry in raw.split(","):
            value = entry.strip()
            if value.startswith(_PROTOCOL_PREFIX):
                token = value[len(_PROTOCOL_PREFIX):]
                if token:
                    return token, value
    token = websocket.query_params.get("token")
    if token:
        return token, None
    return None


def _try_verify(token: str, public_keys: list[str]) -> dict[str, object] | None:
    for public_pem in public_keys:
        try:
            return jwt.decode(token, public_pem, algorithms=[ALGORITHM])  # type: ignore[return-value]
        except jwt.InvalidTokenError:
            continue
    return None


def authenticate(websocket: WebSocket) -> WebSocketIdentity:
    """Validates the JWT token from an incoming WebSocket connection."""
    extracted = _extract_token(websocket)
    if extracted is None:
        raise WebSocketAuthError("missing token")
    token, protocol_value = extracted

    # Try access tokens (identity-issued)
    claims = _try_verify(token, _access_public_keys())
    if claims is not None:
        if claims.get("type") != "access":
            raise WebSocketAuthError("invalid token type")
        return WebSocketIdentity(claims=claims, accepted_subprotocol=protocol_value)

    # Try scanner tokens (gate-issued)
    scanner_keys = _scanner_public_keys()
    if scanner_keys:
        claims = _try_verify(token, scanner_keys)
        if claims is not None and claims.get("type") == "scanner":
            return WebSocketIdentity(claims=claims, accepted_subprotocol=protocol_value)

    raise WebSocketAuthError("invalid token")
