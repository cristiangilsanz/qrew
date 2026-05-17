"""Tests for POST /v1/auth/logout."""

from collections.abc import Iterator
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from com.qode.qrew.v1.service.main import app
from com.qode.qrew.v1.service.routers.auth import get_logout_service
from com.qode.qrew.v1.service.services.logout import LogoutError

_ENDPOINT = "/v1/auth/logout"
_VALID_PAYLOAD: dict[str, object] = {"refresh_token": "a.valid.refresh.token"}


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_service() -> AsyncMock:
    service = AsyncMock()
    service.logout = AsyncMock(return_value=None)
    return service


@pytest.fixture(autouse=True)
def override_dependencies(mock_service: AsyncMock) -> Iterator[None]:
    app.dependency_overrides[get_logout_service] = lambda: mock_service
    yield
    app.dependency_overrides.clear()


# ── Happy path ────────────────────────────────────────────────────────────────


async def test_logout_returns_200(client: AsyncClient, mock_service: AsyncMock) -> None:
    response = await client.post(_ENDPOINT, json=_VALID_PAYLOAD)

    assert response.status_code == 200
    assert "logged out" in response.json()["message"].lower()


async def test_logout_calls_service_with_token(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    await client.post(_ENDPOINT, json=_VALID_PAYLOAD)

    mock_service.logout.assert_awaited_once_with("a.valid.refresh.token")


async def test_expired_token_still_returns_200(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    """Expired tokens are silently accepted — no error, no blacklist entry."""
    response = await client.post(_ENDPOINT, json=_VALID_PAYLOAD)
    assert response.status_code == 200


# ── Error cases (401) ─────────────────────────────────────────────────────────


async def test_returns_401_on_invalid_token(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    mock_service.logout.side_effect = LogoutError("Invalid refresh token")
    response = await client.post(_ENDPOINT, json=_VALID_PAYLOAD)
    assert response.status_code == 401


async def test_returns_401_on_wrong_token_type(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    mock_service.logout.side_effect = LogoutError("Invalid token type")
    response = await client.post(_ENDPOINT, json=_VALID_PAYLOAD)
    assert response.status_code == 401


# ── Input validation (422) ────────────────────────────────────────────────────


async def test_rejects_missing_refresh_token(client: AsyncClient) -> None:
    response = await client.post(_ENDPOINT, json={})
    assert response.status_code == 422


async def test_rejects_empty_refresh_token(client: AsyncClient) -> None:
    response = await client.post(_ENDPOINT, json={"refresh_token": ""})
    assert response.status_code == 422
