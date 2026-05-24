"""Tests for the fingerprint endpoints:
POST /v1/auth/devices/fingerprint
GET  /v1/admin/fingerprints/{fingerprint_hash}
"""

import uuid
from collections.abc import Iterator
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from com.qode.qrew.v1.service.core.auth import get_admin_user, get_current_user
from com.qode.qrew.v1.service.main import app
from com.qode.qrew.v1.service.routers.admin import (
    get_fingerprint_service as get_admin_fingerprint_service,
)
from com.qode.qrew.v1.service.routers.auth import get_fingerprint_service
from com.qode.qrew.v1.service.services.fingerprint import FingerprintService

_AUTH_ENDPOINT = "/v1/auth/devices/fingerprint"
_ADMIN_ENDPOINT_TEMPLATE = "/v1/admin/fingerprints/{hash}"

_VALID_FINGERPRINT_HASH = "abc123def456"
_VALID_BODY = {
    "fingerprint_hash": _VALID_FINGERPRINT_HASH,
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "ip_address": "192.168.1.1",
}


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _mock_user() -> MagicMock:
    user = MagicMock()
    user.id = uuid.uuid4()
    return user


@pytest.fixture
def mock_service() -> AsyncMock:
    service = AsyncMock(spec=FingerprintService)
    service.report = AsyncMock(return_value=False)
    service.get_by_hash = AsyncMock(return_value=[])
    return service


@pytest.fixture(autouse=True)
def override_dependencies(mock_service: AsyncMock) -> Iterator[None]:
    app.dependency_overrides[get_fingerprint_service] = lambda: mock_service
    app.dependency_overrides[get_admin_fingerprint_service] = lambda: mock_service
    app.dependency_overrides[get_current_user] = _mock_user
    app.dependency_overrides[get_admin_user] = _mock_user
    yield
    app.dependency_overrides.clear()


# ── POST /v1/auth/devices/fingerprint ─────────────────────────────────────────


async def test_report_fingerprint_returns_200_not_flagged(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    # Given
    mock_service.report.return_value = False

    # When
    response = await client.post(_AUTH_ENDPOINT, json=_VALID_BODY)

    # Then
    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "Fingerprint recorded."
    assert body["flagged"] is False


async def test_report_fingerprint_returns_200_flagged(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    # Given — service flags the fingerprint (headless or multi-account)
    mock_service.report.return_value = True

    # When
    response = await client.post(_AUTH_ENDPOINT, json=_VALID_BODY)

    # Then
    assert response.status_code == 200
    assert response.json()["flagged"] is True


async def test_report_fingerprint_calls_service_with_correct_args(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    # When
    await client.post(_AUTH_ENDPOINT, json=_VALID_BODY)

    # Then
    mock_service.report.assert_awaited_once()
    _, hash_arg, ua_arg, ip_arg = mock_service.report.call_args[0]
    assert hash_arg == _VALID_FINGERPRINT_HASH
    assert ua_arg == _VALID_BODY["user_agent"]
    assert ip_arg == _VALID_BODY["ip_address"]


async def test_report_fingerprint_accepts_null_optional_fields(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    # When
    response = await client.post(
        _AUTH_ENDPOINT,
        json={"fingerprint_hash": _VALID_FINGERPRINT_HASH},
    )

    # Then
    assert response.status_code == 200


async def test_report_fingerprint_requires_auth(client: AsyncClient) -> None:
    # Given — no current_user override
    app.dependency_overrides.pop(get_current_user, None)

    # When
    response = await client.post(_AUTH_ENDPOINT, json=_VALID_BODY)

    # Then
    assert response.status_code == 401


async def test_report_fingerprint_rejects_missing_hash(
    client: AsyncClient,
) -> None:
    # When
    response = await client.post(
        _AUTH_ENDPOINT,
        json={"user_agent": "Mozilla/5.0"},
    )

    # Then
    assert response.status_code == 422


async def test_report_fingerprint_rejects_empty_hash(
    client: AsyncClient,
) -> None:
    # When
    response = await client.post(
        _AUTH_ENDPOINT,
        json={"fingerprint_hash": ""},
    )

    # Then
    assert response.status_code == 422


# ── GET /v1/admin/fingerprints/{hash} ─────────────────────────────────────────


async def test_get_fingerprint_returns_user_ids(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    # Given
    uid1 = uuid.uuid4()
    uid2 = uuid.uuid4()
    mock_service.get_by_hash.return_value = [uid1, uid2]

    # When
    response = await client.get(
        _ADMIN_ENDPOINT_TEMPLATE.format(hash=_VALID_FINGERPRINT_HASH)
    )

    # Then
    assert response.status_code == 200
    body = response.json()
    assert body["fingerprint_hash"] == _VALID_FINGERPRINT_HASH
    assert body["account_count"] == 2
    assert str(uid1) in body["user_ids"]
    assert str(uid2) in body["user_ids"]


async def test_get_fingerprint_returns_empty_when_hash_unknown(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    # Given
    mock_service.get_by_hash.return_value = []

    # When
    response = await client.get(_ADMIN_ENDPOINT_TEMPLATE.format(hash="unknown-hash"))

    # Then
    assert response.status_code == 200
    body = response.json()
    assert body["account_count"] == 0
    assert body["user_ids"] == []


async def test_get_fingerprint_calls_service_with_hash(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    # When
    await client.get(_ADMIN_ENDPOINT_TEMPLATE.format(hash=_VALID_FINGERPRINT_HASH))

    # Then
    mock_service.get_by_hash.assert_awaited_once_with(_VALID_FINGERPRINT_HASH)


async def test_get_fingerprint_requires_admin(client: AsyncClient) -> None:
    # Given — remove both overrides so the real auth guards run (no valid JWT → 401)
    app.dependency_overrides.pop(get_admin_user, None)
    app.dependency_overrides.pop(get_current_user, None)

    # When
    response = await client.get(
        _ADMIN_ENDPOINT_TEMPLATE.format(hash=_VALID_FINGERPRINT_HASH)
    )

    # Then
    assert response.status_code == 401
