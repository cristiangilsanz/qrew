"""Tests for passkey list, delete, and rename endpoints."""

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from com.qode.qrew.v1.service.main import app
from com.qode.qrew.v1.service.routers.auth import get_passkey_service
from com.qode.qrew.v1.service.schemas.passkey import (
    PasskeyListResponse,
    PasskeyResponse,
)
from com.qode.qrew.v1.service.services.passkey import PasskeyError

_PASSKEY_ID = str(uuid.uuid4())
_ENDPOINT_LIST = "/v1/auth/passkeys"
_ENDPOINT_DELETE = f"/v1/auth/passkeys/{_PASSKEY_ID}"
_ENDPOINT_RENAME = f"/v1/auth/passkeys/{_PASSKEY_ID}"

_SAMPLE_PASSKEY = PasskeyResponse(
    id=_PASSKEY_ID,
    name="My iPhone",
    aaguid="00000000-0000-0000-0000-000000000000",
    last_used_at=datetime.now(UTC),
    created_at=datetime.now(UTC),
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_service() -> AsyncMock:
    service = AsyncMock()
    service.list_passkeys = AsyncMock()
    service.delete_passkey = AsyncMock()
    service.rename_passkey = AsyncMock()
    return service


@pytest.fixture(autouse=True)
def override_dependencies(mock_service: AsyncMock) -> Iterator[None]:
    app.dependency_overrides[get_passkey_service] = lambda: mock_service
    yield
    app.dependency_overrides.clear()


# ── GET /passkeys ──────────────────────────────────────────────────────────────


async def test_list_passkeys_returns_200(
    authenticated_client: AsyncClient, mock_service: AsyncMock
) -> None:
    # Given
    mock_service.list_passkeys.return_value = PasskeyListResponse(
        passkeys=[_SAMPLE_PASSKEY]
    )

    # When
    response = await authenticated_client.get(_ENDPOINT_LIST)

    # Then
    assert response.status_code == 200
    body = response.json()
    assert len(body["passkeys"]) == 1
    assert body["passkeys"][0]["id"] == _PASSKEY_ID
    assert body["passkeys"][0]["name"] == "My iPhone"


async def test_list_passkeys_returns_empty_list(
    authenticated_client: AsyncClient, mock_service: AsyncMock
) -> None:
    # Given
    mock_service.list_passkeys.return_value = PasskeyListResponse(passkeys=[])

    # When
    response = await authenticated_client.get(_ENDPOINT_LIST)

    # Then
    assert response.status_code == 200
    assert response.json()["passkeys"] == []


async def test_list_passkeys_requires_auth(client: AsyncClient) -> None:
    # When
    response = await client.get(_ENDPOINT_LIST)

    # Then
    assert response.status_code == 401


# ── DELETE /passkeys/{id} ──────────────────────────────────────────────────────


async def test_delete_passkey_returns_204(
    authenticated_client: AsyncClient, mock_service: AsyncMock
) -> None:
    # When
    response = await authenticated_client.delete(_ENDPOINT_DELETE)

    # Then
    assert response.status_code == 204
    mock_service.delete_passkey.assert_awaited_once()


async def test_delete_passkey_returns_404_when_not_found(
    authenticated_client: AsyncClient, mock_service: AsyncMock
) -> None:
    # Given
    mock_service.delete_passkey.side_effect = PasskeyError(
        "Passkey not found", field="id"
    )

    # When
    response = await authenticated_client.delete(_ENDPOINT_DELETE)

    # Then
    assert response.status_code == 404


async def test_delete_passkey_returns_409_when_last_passkey(
    authenticated_client: AsyncClient, mock_service: AsyncMock
) -> None:
    # Given
    mock_service.delete_passkey.side_effect = PasskeyError(
        "Cannot delete the last passkey — register a new one first", field="id"
    )

    # When
    response = await authenticated_client.delete(_ENDPOINT_DELETE)

    # Then
    assert response.status_code == 409


async def test_delete_passkey_returns_422_for_invalid_uuid(
    authenticated_client: AsyncClient,
) -> None:
    # When
    response = await authenticated_client.delete("/v1/auth/passkeys/not-a-uuid")

    # Then
    assert response.status_code == 422


async def test_delete_passkey_requires_auth(client: AsyncClient) -> None:
    # When
    response = await client.delete(_ENDPOINT_DELETE)

    # Then
    assert response.status_code == 401


# ── PATCH /passkeys/{id} ───────────────────────────────────────────────────────


async def test_rename_passkey_returns_200(
    authenticated_client: AsyncClient, mock_service: AsyncMock
) -> None:
    # Given
    mock_service.rename_passkey.return_value = PasskeyResponse(
        id=_PASSKEY_ID,
        name="Work Laptop",
        aaguid="00000000-0000-0000-0000-000000000000",
        last_used_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
    )

    # When
    response = await authenticated_client.patch(
        _ENDPOINT_RENAME, json={"name": "Work Laptop"}
    )

    # Then
    assert response.status_code == 200
    assert response.json()["name"] == "Work Laptop"
    mock_service.rename_passkey.assert_awaited_once()


async def test_rename_passkey_returns_404_when_not_found(
    authenticated_client: AsyncClient, mock_service: AsyncMock
) -> None:
    # Given
    mock_service.rename_passkey.side_effect = PasskeyError(
        "Passkey not found", field="id"
    )

    # When
    response = await authenticated_client.patch(
        _ENDPOINT_RENAME, json={"name": "New Name"}
    )

    # Then
    assert response.status_code == 404


async def test_rename_passkey_returns_422_for_invalid_uuid(
    authenticated_client: AsyncClient,
) -> None:
    # When
    response = await authenticated_client.patch(
        "/v1/auth/passkeys/not-a-uuid", json={"name": "New Name"}
    )

    # Then
    assert response.status_code == 422


async def test_rename_passkey_requires_auth(client: AsyncClient) -> None:
    # When
    response = await client.patch(_ENDPOINT_RENAME, json={"name": "New Name"})

    # Then
    assert response.status_code == 401
