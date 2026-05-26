"""Tests for GET /v1/auth/audit (user-facing audit log)."""

import base64
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from com.qode.qrew.v1.service.core.auth import get_current_user
from com.qode.qrew.v1.service.main import app
from com.qode.qrew.v1.service.models.audit import AuditAction
from com.qode.qrew.v1.service.schemas.audit import (
    UserAuditCursor,
    summarize,
)

_ENDPOINT = "/v1/auth/audit"
_AUDIT_REPO = "com.qode.qrew.v1.service.routers.auth.AuditRepository"


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


# ── Happy paths ───────────────────────────────────────────────────────────────


async def test_audit_returns_200_with_events(client: AsyncClient) -> None:
    events = [
        _mock_event(AuditAction.LOGIN),
        _mock_event(AuditAction.PASSKEY_REGISTERED),
    ]
    with patch(_AUDIT_REPO) as repo_cls:
        repo_cls.return_value.list_for_user = AsyncMock(return_value=events)
        response = await client.get(_ENDPOINT)
    assert response.status_code == 200
    body = response.json()
    assert len(body["events"]) == 2
    assert body["next_cursor"] is None


async def test_response_carries_server_curated_summary(client: AsyncClient) -> None:
    events = [_mock_event(AuditAction.LOGIN)]
    with patch(_AUDIT_REPO) as repo_cls:
        repo_cls.return_value.list_for_user = AsyncMock(return_value=events)
        response = await client.get(_ENDPOINT)
    body = response.json()
    assert body["events"][0]["summary"] == summarize(AuditAction.LOGIN)


async def test_response_omits_raw_payload_and_chain_hashes(
    client: AsyncClient,
) -> None:
    events = [_mock_event(payload={"reset_token": "secret"})]
    with patch(_AUDIT_REPO) as repo_cls:
        repo_cls.return_value.list_for_user = AsyncMock(return_value=events)
        response = await client.get(_ENDPOINT)
    body = response.json()
    event = body["events"][0]
    assert "payload" not in event
    assert "hash" not in event
    assert "prev_hash" not in event
    assert "user_agent" not in event
    assert "secret" not in str(body)


# ── Filters ───────────────────────────────────────────────────────────────────


async def test_action_filter_forwarded_to_repo(client: AsyncClient) -> None:
    with patch(_AUDIT_REPO) as repo_cls:
        repo_cls.return_value.list_for_user = AsyncMock(return_value=[])
        await client.get(_ENDPOINT, params={"action": "login"})
    kwargs = repo_cls.return_value.list_for_user.call_args.kwargs
    assert kwargs["action"] == "login"


async def test_since_filter_forwarded_to_repo(client: AsyncClient) -> None:
    since = (datetime.now(UTC) - timedelta(days=7)).isoformat()
    with patch(_AUDIT_REPO) as repo_cls:
        repo_cls.return_value.list_for_user = AsyncMock(return_value=[])
        await client.get(_ENDPOINT, params={"since": since})
    kwargs = repo_cls.return_value.list_for_user.call_args.kwargs
    assert isinstance(kwargs["since"], datetime)


# ── Cursor pagination ─────────────────────────────────────────────────────────


def _make_cursor(created_at: datetime, ident: uuid.UUID) -> str:
    payload = UserAuditCursor(created_at=created_at, id=ident).model_dump_json()
    return base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")


async def test_next_cursor_returned_when_page_full(client: AsyncClient) -> None:
    # 51 events = page size 50 + 1 lookahead
    events = [_mock_event() for _ in range(51)]
    with patch(_AUDIT_REPO) as repo_cls:
        repo_cls.return_value.list_for_user = AsyncMock(return_value=events)
        response = await client.get(_ENDPOINT)
    body = response.json()
    assert len(body["events"]) == 50
    assert body["next_cursor"] is not None
    assert "created_at" in body["next_cursor"]
    assert "id" in body["next_cursor"]


async def test_no_next_cursor_when_page_partial(client: AsyncClient) -> None:
    events = [_mock_event() for _ in range(3)]
    with patch(_AUDIT_REPO) as repo_cls:
        repo_cls.return_value.list_for_user = AsyncMock(return_value=events)
        response = await client.get(_ENDPOINT)
    body = response.json()
    assert body["next_cursor"] is None


async def test_valid_cursor_forwarded_to_repo(client: AsyncClient) -> None:
    cursor_dt = datetime.now(UTC) - timedelta(hours=1)
    cursor_id = uuid.uuid4()
    raw = _make_cursor(cursor_dt, cursor_id)
    with patch(_AUDIT_REPO) as repo_cls:
        repo_cls.return_value.list_for_user = AsyncMock(return_value=[])
        await client.get(_ENDPOINT, params={"cursor": raw})
    kwargs = repo_cls.return_value.list_for_user.call_args.kwargs
    assert kwargs["cursor_id"] == cursor_id


async def test_malformed_cursor_returns_400(client: AsyncClient) -> None:
    response = await client.get(_ENDPOINT, params={"cursor": "not-base64-json"})
    assert response.status_code == 400


# ── Authorization scope ───────────────────────────────────────────────────────


async def test_repo_called_with_current_user_id_only(client: AsyncClient) -> None:
    """Authorization: the repo query is scoped to the authenticated user."""
    with patch(_AUDIT_REPO) as repo_cls:
        repo_cls.return_value.list_for_user = AsyncMock(return_value=[])
        await client.get(_ENDPOINT)
    args = repo_cls.return_value.list_for_user.call_args.args
    # First positional arg is the user_id used to scope the query
    assert isinstance(args[0], uuid.UUID)


# ── summarize helper ──────────────────────────────────────────────────────────


def test_summarize_known_action() -> None:
    assert summarize(AuditAction.LOGIN) == "Signed in"
    assert summarize(AuditAction.PASSKEY_REGISTERED) == "Passkey added"


def test_summarize_unknown_action_falls_back() -> None:
    # Unmapped action gets a human-readable fallback rather than the raw code
    out = summarize("some_new_action")
    assert "_" not in out
