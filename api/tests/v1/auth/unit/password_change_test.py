"""Tests for the POST /v1/auth/change-password endpoint."""

from collections.abc import Iterator
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from com.qode.qrew.v1.service.main import app
from com.qode.qrew.v1.service.routers.auth import get_password_change_service
from com.qode.qrew.v1.service.services.password_change import PasswordChangeError

_ENDPOINT = "/v1/auth/change-password"

_VALID_BODY = {
    "current_password": "OldPass1!",
    "new_password": "N3wS3cur3P@ss!",
}


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_service() -> AsyncMock:
    service = AsyncMock()
    service.change_password = AsyncMock()
    return service


@pytest.fixture(autouse=True)
def override_dependencies(mock_service: AsyncMock) -> Iterator[None]:
    app.dependency_overrides[get_password_change_service] = lambda: mock_service
    yield
    app.dependency_overrides.clear()


# ── POST /change-password ──────────────────────────────────────────────────────


async def test_change_password_returns_200(
    authenticated_client: AsyncClient, mock_service: AsyncMock
) -> None:
    # Given
    mock_service.change_password.return_value = None

    # When
    response = await authenticated_client.post(_ENDPOINT, json=_VALID_BODY)

    # Then
    assert response.status_code == 200
    assert response.json()["message"] == "Password changed successfully."
    mock_service.change_password.assert_awaited_once()


async def test_change_password_returns_400_when_wrong_current_password(
    authenticated_client: AsyncClient, mock_service: AsyncMock
) -> None:
    # Given
    mock_service.change_password.side_effect = PasswordChangeError(
        "Current password is incorrect", field="current_password"
    )

    # When
    response = await authenticated_client.post(_ENDPOINT, json=_VALID_BODY)

    # Then
    assert response.status_code == 400
    assert response.json()["detail"]["field"] == "current_password"


async def test_change_password_returns_400_when_new_password_breached(
    authenticated_client: AsyncClient, mock_service: AsyncMock
) -> None:
    # Given
    mock_service.change_password.side_effect = PasswordChangeError(
        "This password has appeared in a known data breach. Choose a different one",
        field="new_password",
    )

    # When
    response = await authenticated_client.post(_ENDPOINT, json=_VALID_BODY)

    # Then
    assert response.status_code == 400
    assert response.json()["detail"]["field"] == "new_password"


async def test_change_password_returns_422_when_new_password_too_weak(
    authenticated_client: AsyncClient,
) -> None:
    # When
    response = await authenticated_client.post(
        _ENDPOINT,
        json={"current_password": "OldPass1!", "new_password": "password"},
    )

    # Then
    assert response.status_code == 422


async def test_change_password_returns_422_when_new_password_too_short(
    authenticated_client: AsyncClient,
) -> None:
    # When
    response = await authenticated_client.post(
        _ENDPOINT,
        json={"current_password": "OldPass1!", "new_password": "short"},
    )

    # Then
    assert response.status_code == 422


async def test_change_password_requires_auth(client: AsyncClient) -> None:
    # When
    response = await client.post(_ENDPOINT, json=_VALID_BODY)

    # Then
    assert response.status_code == 401
