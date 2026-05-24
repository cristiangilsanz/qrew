"""Tests for POST /v1/auth/change-phone and POST /v1/auth/confirm-phone-change."""

from collections.abc import Iterator
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from com.qode.qrew.v1.service.main import app
from com.qode.qrew.v1.service.routers.auth import get_phone_change_service
from com.qode.qrew.v1.service.services.phone_change import PhoneChangeError

_ENDPOINT_CHANGE = "/v1/auth/change-phone"
_ENDPOINT_CONFIRM = "/v1/auth/confirm-phone-change"

_CHANGE_BODY = {
    "new_phone_number": "+34611222333",
    "current_password": "S3cur3P@ss!",
}
_CONFIRM_BODY = {
    "new_phone_number": "+34611222333",
    "otp": "123456",
}


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_service() -> AsyncMock:
    service = AsyncMock()
    service.request_change = AsyncMock()
    service.confirm_change = AsyncMock()
    return service


@pytest.fixture(autouse=True)
def override_dependencies(mock_service: AsyncMock) -> Iterator[None]:
    app.dependency_overrides[get_phone_change_service] = lambda: mock_service
    yield
    app.dependency_overrides.clear()


# ── POST /change-phone ────────────────────────────────────────────────────────


async def test_change_phone_returns_200(
    authenticated_client: AsyncClient, mock_service: AsyncMock
) -> None:
    # Given
    mock_service.request_change.return_value = None

    # When
    response = await authenticated_client.post(_ENDPOINT_CHANGE, json=_CHANGE_BODY)

    # Then
    assert response.status_code == 200
    assert "new phone" in response.json()["message"]
    mock_service.request_change.assert_awaited_once()


async def test_change_phone_returns_400_when_wrong_password(
    authenticated_client: AsyncClient, mock_service: AsyncMock
) -> None:
    # Given
    mock_service.request_change.side_effect = PhoneChangeError(
        "Current password is incorrect", field="current_password"
    )

    # When
    response = await authenticated_client.post(_ENDPOINT_CHANGE, json=_CHANGE_BODY)

    # Then
    assert response.status_code == 400
    assert response.json()["detail"]["field"] == "current_password"


async def test_change_phone_returns_400_when_same_number(
    authenticated_client: AsyncClient, mock_service: AsyncMock
) -> None:
    # Given
    mock_service.request_change.side_effect = PhoneChangeError(
        "New phone number must be different from the current one",
        field="new_phone_number",
    )

    # When
    response = await authenticated_client.post(_ENDPOINT_CHANGE, json=_CHANGE_BODY)

    # Then
    assert response.status_code == 400
    assert response.json()["detail"]["field"] == "new_phone_number"


async def test_change_phone_returns_400_when_number_taken(
    authenticated_client: AsyncClient, mock_service: AsyncMock
) -> None:
    # Given
    mock_service.request_change.side_effect = PhoneChangeError(
        "Phone number already in use", field="new_phone_number"
    )

    # When
    response = await authenticated_client.post(_ENDPOINT_CHANGE, json=_CHANGE_BODY)

    # Then
    assert response.status_code == 400
    assert response.json()["detail"]["field"] == "new_phone_number"


async def test_change_phone_returns_422_for_invalid_number(
    authenticated_client: AsyncClient,
) -> None:
    # When
    response = await authenticated_client.post(
        _ENDPOINT_CHANGE,
        json={"new_phone_number": "not-a-phone", "current_password": "S3cur3P@ss!"},
    )

    # Then
    assert response.status_code == 422


async def test_change_phone_requires_auth(client: AsyncClient) -> None:
    # When
    response = await client.post(_ENDPOINT_CHANGE, json=_CHANGE_BODY)

    # Then
    assert response.status_code == 401


# ── POST /confirm-phone-change ────────────────────────────────────────────────


async def test_confirm_phone_change_returns_200(
    authenticated_client: AsyncClient, mock_service: AsyncMock
) -> None:
    # Given
    mock_service.confirm_change.return_value = None

    # When
    response = await authenticated_client.post(_ENDPOINT_CONFIRM, json=_CONFIRM_BODY)

    # Then
    assert response.status_code == 200
    assert "updated" in response.json()["message"]
    mock_service.confirm_change.assert_awaited_once()


async def test_confirm_phone_change_returns_400_when_otp_invalid(
    authenticated_client: AsyncClient, mock_service: AsyncMock
) -> None:
    # Given
    mock_service.confirm_change.side_effect = PhoneChangeError(
        "Invalid or expired verification code", field="otp"
    )

    # When
    response = await authenticated_client.post(_ENDPOINT_CONFIRM, json=_CONFIRM_BODY)

    # Then
    assert response.status_code == 400
    assert response.json()["detail"]["field"] == "otp"


async def test_confirm_phone_change_returns_400_when_number_taken(
    authenticated_client: AsyncClient, mock_service: AsyncMock
) -> None:
    # Given
    mock_service.confirm_change.side_effect = PhoneChangeError(
        "This phone number is no longer available", field="new_phone_number"
    )

    # When
    response = await authenticated_client.post(_ENDPOINT_CONFIRM, json=_CONFIRM_BODY)

    # Then
    assert response.status_code == 400
    assert response.json()["detail"]["field"] == "new_phone_number"


async def test_confirm_phone_change_returns_422_for_invalid_otp_format(
    authenticated_client: AsyncClient,
) -> None:
    # When
    response = await authenticated_client.post(
        _ENDPOINT_CONFIRM,
        json={"new_phone_number": "+34611222333", "otp": "abc"},
    )

    # Then
    assert response.status_code == 422


async def test_confirm_phone_change_requires_auth(client: AsyncClient) -> None:
    # When
    response = await client.post(_ENDPOINT_CONFIRM, json=_CONFIRM_BODY)

    # Then
    assert response.status_code == 401
