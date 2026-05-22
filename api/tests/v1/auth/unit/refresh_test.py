"""Tests for POST /v1/auth/refresh."""

from collections.abc import Iterator
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from com.qode.qrew.v1.service.main import app
from com.qode.qrew.v1.service.routers.auth import get_refresh_service
from com.qode.qrew.v1.service.schemas.auth import RefreshResponse
from com.qode.qrew.v1.service.services.refresh import RefreshError

_VALID_PAYLOAD: dict[str, object] = {
    "refresh_token": "a.valid.refresh.token",
}

_ENDPOINT = "/v1/auth/refresh"


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_service() -> AsyncMock:
    service = AsyncMock()
    service.refresh = AsyncMock()
    return service


@pytest.fixture(autouse=True)
def override_dependencies(mock_service: AsyncMock) -> Iterator[None]:
    app.dependency_overrides[get_refresh_service] = lambda: mock_service
    yield
    app.dependency_overrides.clear()


# ── Happy path ────────────────────────────────────────────────────────────────


async def test_refresh_returns_200_with_tokens(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    # Given
    mock_service.refresh.return_value = RefreshResponse(
        access_token="x.y.z", refresh_token="new.refresh.token"
    )

    # When
    response = await client.post(_ENDPOINT, json=_VALID_PAYLOAD)

    # Then
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"] == "x.y.z"
    assert body["refresh_token"] == "new.refresh.token"
    assert body["token_type"] == "bearer"


async def test_refresh_calls_service_with_token(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    # Given
    mock_service.refresh.return_value = RefreshResponse(
        access_token="x.y.z", refresh_token="new.refresh.token"
    )

    # When
    await client.post(_ENDPOINT, json=_VALID_PAYLOAD)

    # Then
    mock_service.refresh.assert_awaited_once()
    call_args = mock_service.refresh.call_args
    assert call_args[0][0].refresh_token == "a.valid.refresh.token"


# ── Input validation (422) ────────────────────────────────────────────────────


async def test_rejects_missing_refresh_token(client: AsyncClient) -> None:
    # When
    response = await client.post(_ENDPOINT, json={})

    # Then
    assert response.status_code == 422


async def test_rejects_empty_refresh_token(client: AsyncClient) -> None:
    # When
    response = await client.post(_ENDPOINT, json={"refresh_token": ""})

    # Then
    assert response.status_code == 422


# ── Auth failures (401) ───────────────────────────────────────────────────────


async def test_returns_401_on_expired_token(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    # Given
    mock_service.refresh.side_effect = RefreshError("Refresh token has expired")

    # When
    response = await client.post(_ENDPOINT, json=_VALID_PAYLOAD)

    # Then
    assert response.status_code == 401


async def test_returns_401_on_invalid_token(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    # Given
    mock_service.refresh.side_effect = RefreshError("Invalid refresh token")

    # When
    response = await client.post(_ENDPOINT, json=_VALID_PAYLOAD)

    # Then
    assert response.status_code == 401


async def test_returns_401_on_wrong_token_type(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    # Given
    mock_service.refresh.side_effect = RefreshError("Invalid token type")

    # When
    response = await client.post(_ENDPOINT, json=_VALID_PAYLOAD)

    # Then
    assert response.status_code == 401


async def test_returns_401_on_inactive_user(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    # Given
    mock_service.refresh.side_effect = RefreshError("Invalid refresh token")

    # When
    response = await client.post(_ENDPOINT, json=_VALID_PAYLOAD)

    # Then
    assert response.status_code == 401


async def test_error_has_no_field(client: AsyncClient, mock_service: AsyncMock) -> None:
    # Given
    mock_service.refresh.side_effect = RefreshError("Invalid refresh token")

    # When
    response = await client.post(_ENDPOINT, json=_VALID_PAYLOAD)

    # Then
    assert response.json()["detail"]["field"] is None


async def test_returns_401_on_revoked_token(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    # Given
    mock_service.refresh.side_effect = RefreshError("Refresh token has been revoked")

    # When
    response = await client.post(_ENDPOINT, json=_VALID_PAYLOAD)

    # Then
    assert response.status_code == 401
