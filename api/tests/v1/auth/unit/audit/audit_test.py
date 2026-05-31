"""Tests for GET /v1/auth/audit (user-facing audit log)."""

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from com.qode.qrew.v1.service.core.auth.auth import get_current_user
from com.qode.qrew.v1.service.main import app
from com.qode.qrew.v1.service.models.audit.audit import AuditAction
from com.qode.qrew.v1.service.schemas.audit.audit import summarize

_ENDPOINT = "/v1/auth/audit"
_PAGINATE = "com.qode.qrew.v1.service.routers.auth.profile.cursor_paginate"
_AUDIT_REPO = "com.qode.qrew.v1.service.routers.auth.profile.AuditRepository"


def _mock_user() -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.is_admin = False
    return u


def _mock_event(
    action: str = AuditAction.LOGIN,
    *,
    created_at: datetime | None = None,
    actor_id: uuid.UUID | None = None,
    ip: str | None = "127.0.0.1",
    payload: dict[str, object] | None = None,
) -> MagicMock:
    e = MagicMock()
    e.id = uuid.uuid4()
    e.actor_id = actor_id or uuid.uuid4()
    e.action = action
    e.entity_type = "user"
    e.ip_address = ip
    e.device_fingerprint_hash = "abc"
    e.user_agent = "ua"
    e.payload = payload or {"sensitive": "data"}
    e.created_at = created_at or datetime.now(UTC)
    return e


@pytest.fixture(autouse=True)
def override_user() -> Iterator[None]:
    app.dependency_overrides[get_current_user] = _mock_user
    yield
    app.dependency_overrides.clear()


async def test_audit_returns_200_with_events(client: AsyncClient) -> None:
    events = [
        _mock_event(AuditAction.LOGIN),
        _mock_event(AuditAction.PASSKEY_REGISTERED),
    ]
    with patch(_PAGINATE, new=AsyncMock(return_value=(events, None))):
        response = await client.get(_ENDPOINT)
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 2
    assert body["next_cursor"] is None


async def test_response_carries_server_curated_summary(client: AsyncClient) -> None:
    events = [_mock_event(AuditAction.LOGIN)]
    with patch(_PAGINATE, new=AsyncMock(return_value=(events, None))):
        response = await client.get(_ENDPOINT)
    body = response.json()
    assert body["items"][0]["summary"] == summarize(AuditAction.LOGIN)


async def test_response_omits_raw_payload_and_chain_hashes(
    client: AsyncClient,
) -> None:
    events = [_mock_event(payload={"reset_token": "secret"})]
    with patch(_PAGINATE, new=AsyncMock(return_value=(events, None))):
        response = await client.get(_ENDPOINT)
    body = response.json()
    event = body["items"][0]
    assert "payload" not in event
    assert "hash" not in event
    assert "prev_hash" not in event
    assert "user_agent" not in event
    assert "secret" not in str(body)


async def test_action_filter_forwarded_to_repo(client: AsyncClient) -> None:
    with (
        patch(_AUDIT_REPO) as repo_cls,
        patch(_PAGINATE, new=AsyncMock(return_value=([], None))),
    ):
        repo_cls.return_value.query_for_user = MagicMock(return_value=MagicMock())
        await client.get(_ENDPOINT, params={"action": "login"})
    kwargs = repo_cls.return_value.query_for_user.call_args.kwargs
    assert kwargs["action"] == "login"


async def test_since_filter_forwarded_to_repo(client: AsyncClient) -> None:
    since = (datetime.now(UTC) - timedelta(days=7)).isoformat()
    with (
        patch(_AUDIT_REPO) as repo_cls,
        patch(_PAGINATE, new=AsyncMock(return_value=([], None))),
    ):
        repo_cls.return_value.query_for_user = MagicMock(return_value=MagicMock())
        await client.get(_ENDPOINT, params={"since": since})
    kwargs = repo_cls.return_value.query_for_user.call_args.kwargs
    assert isinstance(kwargs["since"], datetime)


async def test_next_cursor_returned_when_more_pages(client: AsyncClient) -> None:
    events = [_mock_event() for _ in range(3)]
    with patch(_PAGINATE, new=AsyncMock(return_value=(events, "opaque-token"))):
        response = await client.get(_ENDPOINT)
    body = response.json()
    assert len(body["items"]) == 3
    assert body["next_cursor"] == "opaque-token"


async def test_no_next_cursor_when_page_partial(client: AsyncClient) -> None:
    events = [_mock_event() for _ in range(3)]
    with patch(_PAGINATE, new=AsyncMock(return_value=(events, None))):
        response = await client.get(_ENDPOINT)
    body = response.json()
    assert body["next_cursor"] is None


async def test_malformed_cursor_returns_422(client: AsyncClient) -> None:
    response = await client.get(_ENDPOINT, params={"cursor": "not-base64-json"})
    assert response.status_code == 422


def test_summarize_known_action() -> None:
    assert summarize(AuditAction.LOGIN) == "Signed in"
    assert summarize(AuditAction.PASSKEY_REGISTERED) == "Passkey added"


def test_summarize_unknown_action_falls_back() -> None:
    out = summarize("some_new_action")
    assert "_" not in out
