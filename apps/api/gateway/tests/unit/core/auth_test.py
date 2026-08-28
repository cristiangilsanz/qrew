# tests auth
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from com.qode.qrew.v1.gateway.core.auth import (
    WebSocketAuthError,
    access_public_keys,
    _extract_token,
    scanner_public_keys,
    authenticate,
)
from com.qode.qrew.v1.gateway.core.config import settings

_ec_private = ec.generate_private_key(ec.SECP256R1())
_EC_PRIVATE_PEM = _ec_private.private_bytes(
    serialization.Encoding.PEM,
    serialization.PrivateFormat.PKCS8,
    serialization.NoEncryption(),
).decode()
_EC_PUBLIC_PEM = (
    _ec_private.public_key()
    .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    .decode()
)


# handles make access token
def _make_access_token(user_id: str = "user-1", token_type: str = "access") -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": user_id,
            "type": token_type,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(hours=1)).timestamp()),
        },
        _EC_PRIVATE_PEM,
        algorithm="ES256",
    )


# provides patch access keys
@pytest.fixture(autouse=True)
def patch_access_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "access_jwt_private_key", _EC_PRIVATE_PEM)
    monkeypatch.setattr(settings, "scanner_jwt_private_key", "")
    monkeypatch.setattr(settings, "jwt_audience", "")
    monkeypatch.setattr(settings, "jwt_issuer", "")
    access_public_keys.cache_clear()
    scanner_public_keys.cache_clear()


# handles ws with protocol
def _ws_with_protocol(protocol: str | None) -> MagicMock:
    ws = MagicMock()
    ws.headers = {"sec-websocket-protocol": protocol} if protocol else {}
    return ws


# verifies that extract token parses bearer prefix
def test_extract_token_parses_bearer_prefix() -> None:
    token = "sometoken123"
    ws = _ws_with_protocol(f"bearer.{token}")
    result = _extract_token(ws)
    assert result is not None
    extracted_token, subprotocol = result
    assert extracted_token == token


# verifies that extract token returns none when no header
def test_extract_token_returns_none_when_no_header() -> None:
    ws = _ws_with_protocol(None)
    assert _extract_token(ws) is None


# verifies that extract token returns none without bearer prefix
def test_extract_token_returns_none_without_bearer_prefix() -> None:
    ws = _ws_with_protocol("some-other-protocol")
    assert _extract_token(ws) is None


# verifies that authenticate valid access token
def test_authenticate_valid_access_token() -> None:
    token = _make_access_token()
    ws = _ws_with_protocol(f"bearer.{token}")
    identity = authenticate(ws)
    assert identity.claims["sub"] == "user-1"
    assert identity.claims["type"] == "access"


# verifies that authenticate missing token raises
def test_authenticate_missing_token_raises() -> None:
    ws = _ws_with_protocol(None)
    with pytest.raises(WebSocketAuthError, match="missing token"):
        authenticate(ws)


# verifies that authenticate invalid token raises
def test_authenticate_invalid_token_raises() -> None:
    ws = _ws_with_protocol("bearer.not-a-real-jwt")
    with pytest.raises(WebSocketAuthError):
        authenticate(ws)


# verifies that authenticate wrong type raises
def test_authenticate_wrong_type_raises() -> None:
    token = _make_access_token(token_type="refresh")
    ws = _ws_with_protocol(f"bearer.{token}")
    with pytest.raises(WebSocketAuthError, match="invalid token type"):
        authenticate(ws)
