"""Tests for admin scanner credential endpoints."""

import uuid
from collections.abc import Iterator
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from httpx import AsyncClient

from com.qode.qrew.v1.service.core import auth as auth_module
from com.qode.qrew.v1.service.core.auth import get_admin_user, get_scanner
from com.qode.qrew.v1.service.core.scanner_security import (
    create_scanner_token,
    decode_scanner_token,
    scanner_public_key,
)
from com.qode.qrew.v1.service.core.security import create_access_token
from com.qode.qrew.v1.service.main import app
from com.qode.qrew.v1.service.routers.admin import get_scanner_service
from com.qode.qrew.v1.service.services.scanner import ScannerError, ScannerService

_LIST_ENDPOINT = "/v1/admin/scanners"
_CREATE_ENDPOINT = "/v1/admin/scanners"


def _mock_admin() -> MagicMock:
    user = MagicMock()
    user.id = uuid.uuid4()
    user.is_admin = True
    return user


def _mock_scanner(active: bool = True) -> MagicMock:
    s = MagicMock()
    s.id = uuid.uuid4()
    s.name = "Gate A"
    s.venue_id = uuid.uuid4()
    s.created_by = uuid.uuid4()
    s.created_at = datetime(2026, 1, 1, tzinfo=UTC)
    s.last_used_at = None
    s.is_active = active
    return s


@pytest.fixture
def mock_service() -> AsyncMock:
    service = AsyncMock()
    service.create = AsyncMock(return_value=(_mock_scanner(), "signed.jwt.here"))
    service.list_all = AsyncMock(return_value=[_mock_scanner(), _mock_scanner()])
    service.rotate = AsyncMock(return_value=(_mock_scanner(), "rotated.jwt"))
    service.deactivate = AsyncMock(return_value=_mock_scanner(active=False))
    service.token_ttl_hours = 12
    return service


@pytest.fixture(autouse=True)
def override_deps(mock_service: AsyncMock) -> Iterator[None]:
    app.dependency_overrides[get_admin_user] = _mock_admin
    app.dependency_overrides[get_scanner_service] = lambda: mock_service
    yield
    app.dependency_overrides.clear()


_CREATE_PAYLOAD: dict[str, object] = {
    "name": "Gate A",
    "venue_id": str(uuid.uuid4()),
    "event_id": str(uuid.uuid4()),
    "date": "2026-06-01",
}


# ── POST /admin/scanners ──────────────────────────────────────────────────────


async def test_create_scanner_returns_201_with_token(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    response = await client.post(_CREATE_ENDPOINT, json=_CREATE_PAYLOAD)
    assert response.status_code == 201
    body = response.json()
    assert body["token"] == "signed.jwt.here"
    assert body["token_type"] == "bearer"
    assert body["expires_in_hours"] == 12
    mock_service.create.assert_awaited_once()


async def test_create_rejects_missing_name(client: AsyncClient) -> None:
    payload = dict(_CREATE_PAYLOAD)
    payload.pop("name")
    response = await client.post(_CREATE_ENDPOINT, json=payload)
    assert response.status_code == 422


async def test_create_rejects_invalid_uuid(client: AsyncClient) -> None:
    payload = dict(_CREATE_PAYLOAD)
    payload["venue_id"] = "not-a-uuid"
    response = await client.post(_CREATE_ENDPOINT, json=payload)
    assert response.status_code == 422


# ── GET /admin/scanners ───────────────────────────────────────────────────────


async def test_list_scanners_returns_200(client: AsyncClient) -> None:
    response = await client.get(_LIST_ENDPOINT)
    assert response.status_code == 200
    body = response.json()
    assert len(body["scanners"]) == 2


# ── POST /admin/scanners/{id}/rotate ──────────────────────────────────────────


async def test_rotate_returns_200_with_fresh_token(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    scanner_id = uuid.uuid4()
    response = await client.post(
        f"/v1/admin/scanners/{scanner_id}/rotate",
        json={
            "venue_id": str(uuid.uuid4()),
            "event_id": str(uuid.uuid4()),
            "date": "2026-06-01",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token"] == "rotated.jwt"


async def test_rotate_returns_400_when_scanner_inactive(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    mock_service.rotate.side_effect = ScannerError("Scanner is deactivated")
    response = await client.post(
        f"/v1/admin/scanners/{uuid.uuid4()}/rotate",
        json={
            "venue_id": str(uuid.uuid4()),
            "event_id": str(uuid.uuid4()),
            "date": "2026-06-01",
        },
    )
    assert response.status_code == 400


# ── DELETE /admin/scanners/{id} ───────────────────────────────────────────────


async def test_deactivate_returns_200(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    response = await client.delete(f"/v1/admin/scanners/{uuid.uuid4()}")
    assert response.status_code == 200
    body = response.json()
    assert "deactivated" in body["message"].lower()


async def test_deactivate_returns_400_when_not_found(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    mock_service.deactivate.side_effect = ScannerError("Scanner not found")
    response = await client.delete(f"/v1/admin/scanners/{uuid.uuid4()}")
    assert response.status_code == 400


# ── RS256 signing helpers ─────────────────────────────────────────────────────


def test_create_and_decode_scanner_token_roundtrip() -> None:
    scanner_id = uuid.uuid4()
    venue_id = uuid.uuid4()
    event_id = uuid.uuid4()
    token = create_scanner_token(scanner_id, venue_id, event_id, "2026-06-01")
    payload = decode_scanner_token(token)
    assert payload["type"] == "scanner"
    assert payload["scanner_id"] == str(scanner_id)
    assert payload["venue_id"] == str(venue_id)
    assert payload["event_id"] == str(event_id)
    assert payload["date"] == "2026-06-01"
    assert "iat" in payload
    assert "exp" in payload


def test_scanner_public_key_is_pem() -> None:
    pem = scanner_public_key()
    assert pem.startswith("-----BEGIN PUBLIC KEY-----")
    assert pem.strip().endswith("-----END PUBLIC KEY-----")


# ── get_scanner dependency ────────────────────────────────────────────────────


async def test_get_scanner_returns_active_scanner() -> None:
    """get_scanner decodes the token, finds the scanner row, touches last_used."""
    scanner = _mock_scanner()
    repo_instance = MagicMock()
    repo_instance.get_by_id = AsyncMock(return_value=scanner)
    repo_instance.touch_last_used = AsyncMock()

    # Build a real token
    token = create_scanner_token(
        scanner.id, scanner.venue_id, uuid.uuid4(), "2026-06-01"
    )

    creds = MagicMock()
    creds.credentials = token

    with pytest.MonkeyPatch.context() as mp:

        def _build_repo(_db: object) -> MagicMock:
            return repo_instance

        mp.setattr(auth_module, "ScannerRepository", _build_repo)
        result = await get_scanner(creds, db=MagicMock())

    assert result is scanner
    repo_instance.touch_last_used.assert_awaited_once_with(scanner)


async def test_get_scanner_rejects_inactive_scanner() -> None:

    scanner = _mock_scanner(active=False)
    repo_instance = MagicMock()
    repo_instance.get_by_id = AsyncMock(return_value=scanner)

    token = create_scanner_token(scanner.id, uuid.uuid4(), uuid.uuid4(), "2026-06-01")
    creds = MagicMock()
    creds.credentials = token

    with pytest.MonkeyPatch.context() as mp:

        def _build_repo(_db: object) -> MagicMock:
            return repo_instance

        mp.setattr(auth_module, "ScannerRepository", _build_repo)
        with pytest.raises(HTTPException) as exc:
            await get_scanner(creds, db=MagicMock())
        assert exc.value.status_code == 401


async def test_get_scanner_rejects_unknown_scanner() -> None:

    repo_instance = MagicMock()
    repo_instance.get_by_id = AsyncMock(return_value=None)

    token = create_scanner_token(uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), "2026-06-01")
    creds = MagicMock()
    creds.credentials = token

    with pytest.MonkeyPatch.context() as mp:

        def _build_repo(_db: object) -> MagicMock:
            return repo_instance

        mp.setattr(auth_module, "ScannerRepository", _build_repo)
        with pytest.raises(HTTPException) as exc:
            await get_scanner(creds, db=MagicMock())
        assert exc.value.status_code == 401


async def test_get_scanner_rejects_user_access_token() -> None:
    """An access token (HS256) must NOT validate as a scanner token (RS256)."""

    user_token = create_access_token(str(uuid.uuid4()))
    creds = MagicMock()
    creds.credentials = user_token

    with pytest.raises(HTTPException) as exc:
        await get_scanner(creds, db=MagicMock())
    assert exc.value.status_code == 401


# ── Service-level rotation/deactivation guards ────────────────────────────────


async def test_service_rotate_rejects_venue_mismatch() -> None:

    scanner = _mock_scanner()
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=scanner)
    svc = ScannerService(repo, AsyncMock())

    with pytest.raises(ScannerError, match="different venue"):
        await svc.rotate(uuid.uuid4(), scanner.id, uuid.uuid4(), uuid.uuid4(), _date())


async def test_service_deactivate_rejects_double_deactivation() -> None:

    scanner = _mock_scanner(active=False)
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=scanner)
    svc = ScannerService(repo, AsyncMock())

    with pytest.raises(ScannerError, match="already deactivated"):
        await svc.deactivate(uuid.uuid4(), scanner.id)


def _date() -> date:
    return date(2026, 6, 1)
