"""Tests for cryptographic device-binding endpoints:
POST /v1/auth/devices/bind/begin
POST /v1/auth/devices/bind/complete
"""

import uuid
from collections.abc import Iterator
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from com.qode.qrew.v1.service.core.auth import get_current_user
from com.qode.qrew.v1.service.main import app
from com.qode.qrew.v1.service.routers.auth import get_device_binding_service
from com.qode.qrew.v1.service.services.device_binding import DeviceBindingError

_BEGIN_ENDPOINT = "/v1/auth/devices/bind/begin"
_COMPLETE_ENDPOINT = "/v1/auth/devices/bind/complete"

_FAKE_CHALLENGE = "550e8400-e29b-41d4-a716-446655440000"
_FAKE_DEVICE_ID = uuid.uuid4()

_COMPLETE_BODY = {
    "name": "My Phone",
    "public_key": "MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE",
    "signature": "MEUCIQD",
}


# ── Helpers ───────────────────────────────────────────────────────────────────


def _mock_user() -> MagicMock:
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = "user@example.com"
    return user


def _mock_device() -> MagicMock:
    device = MagicMock()
    device.id = _FAKE_DEVICE_ID
    return device


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_service() -> AsyncMock:
    service = AsyncMock()
    service.begin = AsyncMock(return_value=_FAKE_CHALLENGE)
    service.complete = AsyncMock(return_value=_mock_device())
    return service


@pytest.fixture(autouse=True)
def override_dependencies(mock_service: AsyncMock) -> Iterator[None]:
    app.dependency_overrides[get_device_binding_service] = lambda: mock_service
    app.dependency_overrides[get_current_user] = _mock_user
    yield
    app.dependency_overrides.clear()


# ── bind/begin happy path ─────────────────────────────────────────────────────


async def test_begin_returns_200_with_challenge(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    response = await client.post(_BEGIN_ENDPOINT)

    assert response.status_code == 200
    assert response.json()["challenge"] == _FAKE_CHALLENGE


async def test_begin_calls_service_with_current_user(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    await client.post(_BEGIN_ENDPOINT)

    mock_service.begin.assert_awaited_once()


# ── bind/begin auth guard ─────────────────────────────────────────────────────


async def test_begin_requires_auth(client: AsyncClient) -> None:
    app.dependency_overrides.pop(get_current_user, None)

    response = await client.post(_BEGIN_ENDPOINT)

    assert response.status_code == 401


# ── bind/complete happy path ──────────────────────────────────────────────────


async def test_complete_returns_201_with_device_id(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    response = await client.post(_COMPLETE_ENDPOINT, json=_COMPLETE_BODY)

    assert response.status_code == 201
    body = response.json()
    assert body["device_id"] == str(_FAKE_DEVICE_ID)
    assert "successfully" in body["message"].lower()


async def test_complete_calls_service_with_body_fields(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    await client.post(_COMPLETE_ENDPOINT, json=_COMPLETE_BODY)

    mock_service.complete.assert_awaited_once_with(
        mock_service.complete.call_args[0][0],
        _COMPLETE_BODY["name"],
        _COMPLETE_BODY["public_key"],
        _COMPLETE_BODY["signature"],
    )


# ── bind/complete validation ──────────────────────────────────────────────────


async def test_complete_requires_name_field(client: AsyncClient) -> None:
    body = {k: v for k, v in _COMPLETE_BODY.items() if k != "name"}

    response = await client.post(_COMPLETE_ENDPOINT, json=body)

    assert response.status_code == 422


async def test_complete_requires_public_key_field(client: AsyncClient) -> None:
    body = {k: v for k, v in _COMPLETE_BODY.items() if k != "public_key"}

    response = await client.post(_COMPLETE_ENDPOINT, json=body)

    assert response.status_code == 422


async def test_complete_requires_signature_field(client: AsyncClient) -> None:
    body = {k: v for k, v in _COMPLETE_BODY.items() if k != "signature"}

    response = await client.post(_COMPLETE_ENDPOINT, json=body)

    assert response.status_code == 422


# ── bind/complete error handling ──────────────────────────────────────────────


async def test_complete_returns_400_on_expired_challenge(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    mock_service.complete = AsyncMock(
        side_effect=DeviceBindingError(
            "Binding session expired. Please start again.", field=None
        )
    )

    response = await client.post(_COMPLETE_ENDPOINT, json=_COMPLETE_BODY)

    assert response.status_code == 400
    assert "expired" in response.json()["detail"]["message"]


async def test_complete_returns_400_on_duplicate_key(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    mock_service.complete = AsyncMock(
        side_effect=DeviceBindingError(
            "This key is already registered.", field="public_key"
        )
    )

    response = await client.post(_COMPLETE_ENDPOINT, json=_COMPLETE_BODY)

    assert response.status_code == 400
    assert "registered" in response.json()["detail"]["message"]


async def test_complete_returns_400_on_invalid_signature(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    mock_service.complete = AsyncMock(
        side_effect=DeviceBindingError(
            "Signature verification failed.", field="signature"
        )
    )

    response = await client.post(_COMPLETE_ENDPOINT, json=_COMPLETE_BODY)

    assert response.status_code == 400
    assert "signature" in response.json()["detail"]["message"].lower()


async def test_complete_requires_auth(client: AsyncClient) -> None:
    app.dependency_overrides.pop(get_current_user, None)

    response = await client.post(_COMPLETE_ENDPOINT, json=_COMPLETE_BODY)

    assert response.status_code == 401
