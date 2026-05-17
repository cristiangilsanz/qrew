"""Tests for POST /v1/auth/complete-setup."""

from collections.abc import Iterator
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from com.qode.qrew.v1.service.core.auth import get_setup_or_full_user
from com.qode.qrew.v1.service.main import app
from com.qode.qrew.v1.service.routers.auth import get_complete_setup_service
from com.qode.qrew.v1.service.schemas.auth import LoginResponse
from com.qode.qrew.v1.service.services.complete_setup import SetupError

_ENDPOINT = "/v1/auth/complete-setup"


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _mock_user() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_service() -> AsyncMock:
    service = AsyncMock()
    service.complete = AsyncMock()
    return service


@pytest.fixture(autouse=True)
def override_dependencies(mock_service: AsyncMock) -> Iterator[None]:
    app.dependency_overrides[get_complete_setup_service] = lambda: mock_service
    app.dependency_overrides[get_setup_or_full_user] = _mock_user
    yield
    app.dependency_overrides.clear()


# ── Happy path ────────────────────────────────────────────────────────────────


async def test_complete_setup_returns_200_with_full_tokens(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    mock_service.complete.return_value = LoginResponse(
        access_token="full.access.token",
        refresh_token="full.refresh.token",
    )

    response = await client.post(_ENDPOINT)

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"] == "full.access.token"
    assert body["refresh_token"] == "full.refresh.token"
    assert body["setup_required"] is False


async def test_complete_setup_calls_service_with_current_user(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    mock_service.complete.return_value = LoginResponse(
        access_token="a.b.c", refresh_token="d.e.f"
    )
    await client.post(_ENDPOINT)
    mock_service.complete.assert_awaited_once()


# ── Incomplete setup (400) ────────────────────────────────────────────────────


async def test_returns_400_when_phone_not_verified(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    mock_service.complete.side_effect = SetupError(
        "Phone number is not verified", field="phone_number"
    )
    response = await client.post(_ENDPOINT)
    assert response.status_code == 400
    assert response.json()["detail"]["field"] == "phone_number"


async def test_returns_400_when_kyc_not_submitted(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    mock_service.complete.side_effect = SetupError(
        "KYC document has not been submitted", field="kyc"
    )
    response = await client.post(_ENDPOINT)
    assert response.status_code == 400
    assert response.json()["detail"]["field"] == "kyc"


async def test_returns_400_when_passkey_not_registered(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    mock_service.complete.side_effect = SetupError(
        "Passkey has not been registered", field="passkey"
    )
    response = await client.post(_ENDPOINT)
    assert response.status_code == 400
    assert response.json()["detail"]["field"] == "passkey"
