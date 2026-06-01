from unittest.mock import AsyncMock, MagicMock

import pytest

from com.qode.qrew.v1.service.core.ws import auth as ws_auth_module
from com.qode.qrew.v1.service.core.ws.auth import (
    WebSocketAuthError,
    authenticate,
    extract_token,
)


def _ws_with(protocol: str | None = None, query_token: str | None = None) -> MagicMock:
    ws = MagicMock()
    ws.headers = {}
    if protocol is not None:
        ws.headers["sec-websocket-protocol"] = protocol
    ws.query_params = {"token": query_token} if query_token else {}
    return ws


def test_extract_from_subprotocol() -> None:
    ws = _ws_with(protocol="bearer.abc123")
    result = extract_token(ws)
    assert result == ("abc123", "bearer.abc123")


def test_extract_from_query_string_fallback() -> None:
    ws = _ws_with(query_token="xyz")
    result = extract_token(ws)
    assert result == ("xyz", None)


def test_extract_returns_none_when_absent() -> None:
    ws = _ws_with()
    assert extract_token(ws) is None


async def test_authenticate_rejects_missing_token() -> None:
    ws = _ws_with()
    with pytest.raises(WebSocketAuthError, match="missing token"):
        await authenticate(ws, MagicMock(), AsyncMock())


async def test_authenticate_rejects_setup_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _verify(_purpose: str, _token: str) -> dict[str, str]:
        return {"type": "setup", "scope": "setup", "jti": "j"}

    monkeypatch.setattr(ws_auth_module.jwt_keys, "verify", _verify)
    ws = _ws_with(protocol="bearer.tok")
    with pytest.raises(WebSocketAuthError, match="invalid token type"):
        await authenticate(ws, MagicMock(), AsyncMock())
