"""Tests for POST /v1/auth/passkey/register/begin and /complete."""

import json
from collections.abc import Iterator
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from com.qode.qrew.v1.service.core.auth import get_setup_or_full_user
from com.qode.qrew.v1.service.main import app
from com.qode.qrew.v1.service.routers.auth import get_passkey_service
from com.qode.qrew.v1.service.services.passkey import PasskeyError

_BEGIN_ENDPOINT = "/v1/auth/passkey/register/begin"
_COMPLETE_ENDPOINT = "/v1/auth/passkey/register/complete"

_VALID_COMPLETE_PAYLOAD: dict[str, object] = {
    "id": "Y2hlY2tNZQ",
    "rawId": "Y2hlY2tNZQ",
    "response": {
        "clientDataJSON": "eyJ0eXBlIjoid2ViYXV0aG4uY3JlYXRlIn0",
        "attestationObject": "o2NmbXRkbm9uZWdhdHRTdG10oGhhdXRoRGF0YVik",
    },
    "type": "public-key",
}

_FAKE_OPTIONS = json.dumps(
    {
        "rp": {"name": "Qrew", "id": "localhost"},
        "user": {"id": "dXNlcklk", "name": "alice@example.com", "displayName": "Alice"},
        "challenge": "Y2hhbGxlbmdl",
        "pubKeyCredParams": [{"type": "public-key", "alg": -7}],
        "timeout": 60000,
        "attestation": "none",
    }
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _mock_user() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_service() -> AsyncMock:
    service = AsyncMock()
    service.begin_registration = AsyncMock(return_value=_FAKE_OPTIONS)
    service.complete_registration = AsyncMock(return_value=None)
    return service


@pytest.fixture(autouse=True)
def override_dependencies(mock_service: AsyncMock) -> Iterator[None]:
    app.dependency_overrides[get_passkey_service] = lambda: mock_service
    app.dependency_overrides[get_setup_or_full_user] = _mock_user
    yield
    app.dependency_overrides.clear()


# ── begin ─────────────────────────────────────────────────────────────────────


async def test_begin_returns_200_with_options(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    response = await client.post(_BEGIN_ENDPOINT)

    assert response.status_code == 200
    body = response.json()
    assert body["rp"]["name"] == "Qrew"
    assert "challenge" in body


async def test_begin_calls_service_with_current_user(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    await client.post(_BEGIN_ENDPOINT)
    mock_service.begin_registration.assert_awaited_once()


# ── complete ──────────────────────────────────────────────────────────────────


async def test_complete_returns_200(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    response = await client.post(_COMPLETE_ENDPOINT, json=_VALID_COMPLETE_PAYLOAD)

    assert response.status_code == 200
    assert "registered" in response.json()["message"].lower()


async def test_complete_calls_service_with_credential(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    await client.post(_COMPLETE_ENDPOINT, json=_VALID_COMPLETE_PAYLOAD)
    mock_service.complete_registration.assert_awaited_once()


async def test_complete_returns_400_on_expired_challenge(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    mock_service.complete_registration.side_effect = PasskeyError(
        "Registration session expired. Please start again."
    )
    response = await client.post(_COMPLETE_ENDPOINT, json=_VALID_COMPLETE_PAYLOAD)
    assert response.status_code == 400


async def test_complete_returns_400_on_verification_failure(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    mock_service.complete_registration.side_effect = PasskeyError(
        "Passkey registration failed. Please try again."
    )
    response = await client.post(_COMPLETE_ENDPOINT, json=_VALID_COMPLETE_PAYLOAD)
    assert response.status_code == 400


# ── Input validation (422) ────────────────────────────────────────────────────


async def test_complete_rejects_missing_id(client: AsyncClient) -> None:
    payload = {k: v for k, v in _VALID_COMPLETE_PAYLOAD.items() if k != "id"}
    response = await client.post(_COMPLETE_ENDPOINT, json=payload)
    assert response.status_code == 422


async def test_complete_rejects_missing_response(client: AsyncClient) -> None:
    payload = {k: v for k, v in _VALID_COMPLETE_PAYLOAD.items() if k != "response"}
    response = await client.post(_COMPLETE_ENDPOINT, json=payload)
    assert response.status_code == 422
