"""Tests for device management endpoints:
GET  /v1/auth/devices
POST /v1/auth/devices/{device_id}/revoke
POST /v1/auth/devices/revoke-all
"""

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from com.qode.qrew.v1.service.core.auth.auth import get_current_user
from com.qode.qrew.v1.service.main import app
from com.qode.qrew.v1.service.routers.auth import get_device_service
from com.qode.qrew.v1.service.services.device.device import DeviceError

_LIST_ENDPOINT = "/v1/auth/devices"
_REVOKE_ALL_ENDPOINT = "/v1/auth/devices/revoke-all"

_DEVICE_ID = uuid.uuid4()
_OTHER_DEVICE_ID = uuid.uuid4()
_CALLING_DEVICE_ID = uuid.uuid4()


def _mock_user() -> MagicMock:
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = "user@example.com"
    return user


def _mock_device(device_id: uuid.UUID = _DEVICE_ID) -> MagicMock:
    device = MagicMock()
    device.id = device_id
    device.name = "Test Phone"
    device.created_at = datetime(2026, 1, 1, tzinfo=UTC)
    device.last_seen_at = datetime(2026, 5, 1, tzinfo=UTC)
    return device


@pytest.fixture
def mock_service() -> AsyncMock:
    service = AsyncMock()
    service.list_devices = AsyncMock(
        return_value=[_mock_device(), _mock_device(_OTHER_DEVICE_ID)]
    )
    service.revoke_device = AsyncMock(return_value=None)
    service.revoke_all_devices = AsyncMock(return_value=2)
    return service


@pytest.fixture(autouse=True)
def override_dependencies(mock_service: AsyncMock) -> Iterator[None]:
    app.dependency_overrides[get_device_service] = lambda: mock_service
    app.dependency_overrides[get_current_user] = _mock_user
    yield
    app.dependency_overrides.clear()


async def test_list_devices_returns_200_with_devices(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    response = await client.get(_LIST_ENDPOINT)

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 2
    assert body["items"][0]["name"] == "Test Phone"
    assert "id" in body["items"][0]
    assert "created_at" in body["items"][0]
    assert body["next_cursor"] is None


async def test_list_devices_calls_service(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    await client.get(_LIST_ENDPOINT)

    mock_service.list_devices.assert_awaited_once()


async def test_list_devices_returns_empty_list_when_no_devices(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    mock_service.list_devices = AsyncMock(return_value=[])

    response = await client.get(_LIST_ENDPOINT)

    assert response.status_code == 200
    assert response.json()["items"] == []


async def test_list_devices_requires_auth(client: AsyncClient) -> None:
    app.dependency_overrides.pop(get_current_user, None)

    response = await client.get(_LIST_ENDPOINT)

    assert response.status_code == 401


async def test_revoke_device_returns_200(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    response = await client.post(f"/v1/auth/devices/{_DEVICE_ID}/revoke")

    assert response.status_code == 200
    assert "revoked" in response.json()["message"].lower()


async def test_revoke_device_calls_service_with_device_id(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    await client.post(f"/v1/auth/devices/{_DEVICE_ID}/revoke")

    mock_service.revoke_device.assert_awaited_once()
    call_args = mock_service.revoke_device.call_args[0]
    assert call_args[1] == _DEVICE_ID


async def test_revoke_device_passes_calling_device_header(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    await client.post(
        f"/v1/auth/devices/{_DEVICE_ID}/revoke",
        headers={"X-Calling-Device-Id": str(_CALLING_DEVICE_ID)},
    )

    call_args = mock_service.revoke_device.call_args[0]
    assert call_args[2] == _CALLING_DEVICE_ID


async def test_revoke_device_returns_400_on_not_found(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    mock_service.revoke_device = AsyncMock(
        side_effect=DeviceError("Device not found.", field=None)
    )

    response = await client.post(f"/v1/auth/devices/{_DEVICE_ID}/revoke")

    assert response.status_code == 400
    assert "not found" in response.json()["detail"]["message"]


async def test_revoke_device_returns_400_on_already_revoked(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    mock_service.revoke_device = AsyncMock(
        side_effect=DeviceError("Device is already revoked.", field=None)
    )

    response = await client.post(f"/v1/auth/devices/{_DEVICE_ID}/revoke")

    assert response.status_code == 400
    assert "already revoked" in response.json()["detail"]["message"]


async def test_revoke_device_returns_400_on_self_revoke(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    mock_service.revoke_device = AsyncMock(
        side_effect=DeviceError(
            "Cannot revoke the device you are currently using.", field=None
        )
    )

    response = await client.post(
        f"/v1/auth/devices/{_DEVICE_ID}/revoke",
        headers={"X-Calling-Device-Id": str(_DEVICE_ID)},
    )

    assert response.status_code == 400
    assert "currently using" in response.json()["detail"]["message"]


async def test_revoke_device_requires_auth(client: AsyncClient) -> None:
    app.dependency_overrides.pop(get_current_user, None)

    response = await client.post(f"/v1/auth/devices/{_DEVICE_ID}/revoke")

    assert response.status_code == 401


async def test_revoke_device_ignores_malformed_calling_device_header(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    response = await client.post(
        f"/v1/auth/devices/{_DEVICE_ID}/revoke",
        headers={"X-Calling-Device-Id": "not-a-uuid"},
    )

    assert response.status_code == 200
    call_args = mock_service.revoke_device.call_args[0]
    assert call_args[2] is None


async def test_revoke_all_returns_200_with_count(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    response = await client.post(_REVOKE_ALL_ENDPOINT)

    assert response.status_code == 200
    body = response.json()
    assert body["revoked_count"] == 2
    assert "2" in body["message"]


async def test_revoke_all_calls_service(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    await client.post(_REVOKE_ALL_ENDPOINT)

    mock_service.revoke_all_devices.assert_awaited_once()


async def test_revoke_all_passes_calling_device_header(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    await client.post(
        _REVOKE_ALL_ENDPOINT,
        headers={"X-Calling-Device-Id": str(_CALLING_DEVICE_ID)},
    )

    call_args = mock_service.revoke_all_devices.call_args[0]
    assert call_args[1] == _CALLING_DEVICE_ID


async def test_revoke_all_returns_zero_when_no_devices(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    mock_service.revoke_all_devices = AsyncMock(return_value=0)

    response = await client.post(_REVOKE_ALL_ENDPOINT)

    assert response.status_code == 200
    assert response.json()["revoked_count"] == 0


async def test_revoke_all_requires_auth(client: AsyncClient) -> None:
    app.dependency_overrides.pop(get_current_user, None)

    response = await client.post(_REVOKE_ALL_ENDPOINT)

    assert response.status_code == 401
