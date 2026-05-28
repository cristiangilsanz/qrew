"""Tests for session management endpoints."""

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from com.qode.qrew.v1.service.main import app
from com.qode.qrew.v1.service.routers.auth import get_session_service
from com.qode.qrew.v1.service.schemas.auth.session import (
    SessionResponse,
)
from com.qode.qrew.v1.service.services.session.session import SessionError

_ENDPOINT_LIST = "/v1/auth/sessions"
_ENDPOINT_REVOKE_ALL = "/v1/auth/sessions/revoke-all"
_JTI = "test-jti-value"
_ENDPOINT_REVOKE = f"/v1/auth/sessions/{_JTI}"

_SAMPLE_SESSION = SessionResponse(
    id=str(uuid.uuid4()),
    jti=_JTI,
    ip_address="1.2.3.4",
    user_agent="Mozilla/5.0",
    device_fingerprint=None,
    created_at=datetime.now(UTC),
    last_used_at=datetime.now(UTC),
)


@pytest.fixture
def mock_service() -> AsyncMock:
    service = AsyncMock()
    service.list_sessions = AsyncMock()
    service.revoke_session = AsyncMock()
    service.revoke_all = AsyncMock()
    return service


@pytest.fixture(autouse=True)
def override_dependencies(mock_service: AsyncMock) -> Iterator[None]:
    app.dependency_overrides[get_session_service] = lambda: mock_service
    yield
    app.dependency_overrides.clear()


async def test_list_sessions_returns_200(
    authenticated_client: AsyncClient, mock_service: AsyncMock
) -> None:
    mock_service.list_sessions.return_value = [_SAMPLE_SESSION]

    response = await authenticated_client.get(_ENDPOINT_LIST)

    assert response.status_code == 200
    body = response.json()
    assert len(body["sessions"]) == 1
    assert body["sessions"][0]["jti"] == _JTI


async def test_list_sessions_returns_empty_list(
    authenticated_client: AsyncClient, mock_service: AsyncMock
) -> None:
    mock_service.list_sessions.return_value = []

    response = await authenticated_client.get(_ENDPOINT_LIST)

    assert response.status_code == 200
    assert response.json()["sessions"] == []


async def test_list_sessions_requires_auth(client: AsyncClient) -> None:
    response = await client.get(_ENDPOINT_LIST)

    assert response.status_code == 401


async def test_revoke_session_returns_204(
    authenticated_client: AsyncClient, mock_service: AsyncMock
) -> None:
    response = await authenticated_client.delete(_ENDPOINT_REVOKE)

    assert response.status_code == 204
    mock_service.revoke_session.assert_awaited_once()


async def test_revoke_session_returns_404_when_not_found(
    authenticated_client: AsyncClient, mock_service: AsyncMock
) -> None:
    mock_service.revoke_session.side_effect = SessionError(
        "Session not found", field="jti"
    )

    response = await authenticated_client.delete(_ENDPOINT_REVOKE)

    assert response.status_code == 404


async def test_revoke_session_requires_auth(client: AsyncClient) -> None:
    response = await client.delete(_ENDPOINT_REVOKE)

    assert response.status_code == 401


async def test_revoke_all_returns_200(
    authenticated_client: AsyncClient, mock_service: AsyncMock
) -> None:
    response = await authenticated_client.post(_ENDPOINT_REVOKE_ALL)

    assert response.status_code == 200
    assert "revoked" in response.json()["message"].lower()
    mock_service.revoke_all.assert_awaited_once()


async def test_revoke_all_requires_auth(client: AsyncClient) -> None:
    response = await client.post(_ENDPOINT_REVOKE_ALL)

    assert response.status_code == 401
