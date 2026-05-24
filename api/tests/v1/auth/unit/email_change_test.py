"""Tests for POST /v1/auth/change-email and POST /v1/auth/confirm-email-change."""

from collections.abc import Iterator
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from com.qode.qrew.v1.service.main import app
from com.qode.qrew.v1.service.routers.auth import get_email_change_service
from com.qode.qrew.v1.service.services.email_change import EmailChangeError

_ENDPOINT_CHANGE = "/v1/auth/change-email"
_ENDPOINT_CONFIRM = "/v1/auth/confirm-email-change"

_CHANGE_BODY = {
    "new_email": "new@example.com",
    "current_password": "S3cur3P@ss!",
}
_CONFIRM_BODY = {"token": "somevalidtoken"}


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_service() -> AsyncMock:
    service = AsyncMock()
    service.request_change = AsyncMock()
    service.confirm_change = AsyncMock()
    return service


@pytest.fixture(autouse=True)
def override_dependencies(mock_service: AsyncMock) -> Iterator[None]:
    app.dependency_overrides[get_email_change_service] = lambda: mock_service
    yield
    app.dependency_overrides.clear()


# ── POST /change-email ────────────────────────────────────────────────────────


async def test_change_email_returns_200(
    authenticated_client: AsyncClient, mock_service: AsyncMock
) -> None:
    # Given
    mock_service.request_change.return_value = None

    # When
    response = await authenticated_client.post(_ENDPOINT_CHANGE, json=_CHANGE_BODY)

    # Then
    assert response.status_code == 200
    assert "new email" in response.json()["message"]
    mock_service.request_change.assert_awaited_once()


async def test_change_email_returns_400_when_wrong_password(
    authenticated_client: AsyncClient, mock_service: AsyncMock
) -> None:
    # Given
    mock_service.request_change.side_effect = EmailChangeError(
        "Current password is incorrect", field="current_password"
    )

    # When
    response = await authenticated_client.post(_ENDPOINT_CHANGE, json=_CHANGE_BODY)

    # Then
    assert response.status_code == 400
    assert response.json()["detail"]["field"] == "current_password"


async def test_change_email_returns_400_when_same_email(
    authenticated_client: AsyncClient, mock_service: AsyncMock
) -> None:
    # Given
    mock_service.request_change.side_effect = EmailChangeError(
        "New email must be different from the current one", field="new_email"
    )

    # When
    response = await authenticated_client.post(_ENDPOINT_CHANGE, json=_CHANGE_BODY)

    # Then
    assert response.status_code == 400
    assert response.json()["detail"]["field"] == "new_email"


async def test_change_email_returns_400_when_email_taken(
    authenticated_client: AsyncClient, mock_service: AsyncMock
) -> None:
    # Given
    mock_service.request_change.side_effect = EmailChangeError(
        "Email already in use", field="new_email"
    )

    # When
    response = await authenticated_client.post(_ENDPOINT_CHANGE, json=_CHANGE_BODY)

    # Then
    assert response.status_code == 400
    assert response.json()["detail"]["field"] == "new_email"


async def test_change_email_returns_422_for_invalid_email(
    authenticated_client: AsyncClient,
) -> None:
    # When
    response = await authenticated_client.post(
        _ENDPOINT_CHANGE,
        json={"new_email": "not-an-email", "current_password": "S3cur3P@ss!"},
    )

    # Then
    assert response.status_code == 422


async def test_change_email_requires_auth(client: AsyncClient) -> None:
    # When
    response = await client.post(_ENDPOINT_CHANGE, json=_CHANGE_BODY)

    # Then
    assert response.status_code == 401


# ── POST /confirm-email-change ────────────────────────────────────────────────


async def test_confirm_email_change_returns_200(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    # Given
    mock_service.confirm_change.return_value = None

    # When
    response = await client.post(_ENDPOINT_CONFIRM, json=_CONFIRM_BODY)

    # Then
    assert response.status_code == 200
    assert "updated" in response.json()["message"]
    mock_service.confirm_change.assert_awaited_once()


async def test_confirm_email_change_returns_400_when_token_invalid(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    # Given
    mock_service.confirm_change.side_effect = EmailChangeError(
        "Invalid or expired token", field="token"
    )

    # When
    response = await client.post(_ENDPOINT_CONFIRM, json=_CONFIRM_BODY)

    # Then
    assert response.status_code == 400
    assert response.json()["detail"]["field"] == "token"


async def test_confirm_email_change_returns_400_when_email_no_longer_available(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    # Given
    mock_service.confirm_change.side_effect = EmailChangeError(
        "This email address is no longer available", field="token"
    )

    # When
    response = await client.post(_ENDPOINT_CONFIRM, json=_CONFIRM_BODY)

    # Then
    assert response.status_code == 400
