"""Tests for device-bound session creation and refresh validation."""

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from com.qode.qrew.v1.service.core.auth import jwt_keys
from com.qode.qrew.v1.service.core.auth.security import (
    create_access_token,
    create_refresh_token,
    extract_jti,
)
from com.qode.qrew.v1.service.main import app
from com.qode.qrew.v1.service.routers.auth import (
    get_login_service,
    get_refresh_service,
)
from com.qode.qrew.v1.service.schemas.auth.auth import (
    LoginResponse,
    RefreshResponse,
)
from com.qode.qrew.v1.service.services.auth.login import LoginService

_LOGIN_ENDPOINT = "/v1/auth/login"
_REFRESH_ENDPOINT = "/v1/auth/refresh"


@pytest.fixture
def mock_login_service() -> AsyncMock:
    service = AsyncMock()
    service.login = AsyncMock(
        return_value=LoginResponse(access_token="a.b.c", refresh_token="d.e.f")
    )
    return service


@pytest.fixture
def mock_refresh_service() -> AsyncMock:
    service = AsyncMock()
    service.refresh = AsyncMock(
        return_value=RefreshResponse(access_token="x.y.z", refresh_token="r.s.t")
    )
    return service


@pytest.fixture(autouse=True)
def override_dependencies(
    mock_login_service: AsyncMock, mock_refresh_service: AsyncMock
) -> Iterator[None]:
    app.dependency_overrides[get_login_service] = lambda: mock_login_service
    app.dependency_overrides[get_refresh_service] = lambda: mock_refresh_service
    yield
    app.dependency_overrides.clear()


def test_access_token_omits_device_id_when_not_provided() -> None:
    token = create_access_token("user-123")
    payload = jwt_keys.verify(jwt_keys.ACCESS, token)
    assert "device_id" not in payload


def test_access_token_includes_device_id_when_provided() -> None:
    device_id = str(uuid.uuid4())
    token = create_access_token("user-123", device_id=device_id)
    payload = jwt_keys.verify(jwt_keys.ACCESS, token)
    assert payload["device_id"] == device_id


async def test_login_passes_device_id_from_header(
    client: AsyncClient, mock_login_service: AsyncMock
) -> None:
    device_id = uuid.uuid4()
    await client.post(
        _LOGIN_ENDPOINT,
        json={"email": "a@b.com", "password": "x"},
        headers={"X-Device-Id": str(device_id)},
    )
    mock_login_service.login.assert_awaited_once()
    args = mock_login_service.login.call_args.args
    assert args[4] == device_id


async def test_login_passes_none_when_header_missing(
    client: AsyncClient, mock_login_service: AsyncMock
) -> None:
    await client.post(_LOGIN_ENDPOINT, json={"email": "a@b.com", "password": "x"})
    args = mock_login_service.login.call_args.args
    assert args[4] is None


async def test_login_silently_ignores_malformed_device_id(
    client: AsyncClient, mock_login_service: AsyncMock
) -> None:
    await client.post(
        _LOGIN_ENDPOINT,
        json={"email": "a@b.com", "password": "x"},
        headers={"X-Device-Id": "not-a-uuid"},
    )
    args = mock_login_service.login.call_args.args
    assert args[4] is None


async def test_login_service_resolves_valid_bound_device() -> None:

    user_id = uuid.uuid4()
    device_id = uuid.uuid4()
    device = type("D", (), {"id": device_id, "user_id": user_id, "revoked_at": None})()
    device_repo = AsyncMock()
    device_repo.get_by_id = AsyncMock(return_value=device)

    svc = LoginService(AsyncMock(), AsyncMock(), AsyncMock(), device_repo=device_repo)
    result = await svc.resolve_bound_device(user_id, device_id)
    assert result == device_id


async def test_login_service_rejects_device_owned_by_other_user() -> None:

    user_id = uuid.uuid4()
    device_id = uuid.uuid4()
    device = type(
        "D",
        (),
        {"id": device_id, "user_id": uuid.uuid4(), "revoked_at": None},
    )()
    device_repo = AsyncMock()
    device_repo.get_by_id = AsyncMock(return_value=device)

    svc = LoginService(AsyncMock(), AsyncMock(), AsyncMock(), device_repo=device_repo)
    result = await svc.resolve_bound_device(user_id, device_id)
    assert result is None


async def test_login_service_rejects_revoked_device() -> None:

    user_id = uuid.uuid4()
    device_id = uuid.uuid4()
    device = type(
        "D",
        (),
        {"id": device_id, "user_id": user_id, "revoked_at": datetime.now(UTC)},
    )()
    device_repo = AsyncMock()
    device_repo.get_by_id = AsyncMock(return_value=device)

    svc = LoginService(AsyncMock(), AsyncMock(), AsyncMock(), device_repo=device_repo)
    result = await svc.resolve_bound_device(user_id, device_id)
    assert result is None


async def test_login_service_returns_none_when_device_id_missing() -> None:

    device_repo = AsyncMock()
    svc = LoginService(AsyncMock(), AsyncMock(), AsyncMock(), device_repo=device_repo)
    result = await svc.resolve_bound_device(uuid.uuid4(), None)
    assert result is None
    device_repo.get_by_id.assert_not_called()


def test_refresh_token_jti_extractable() -> None:
    """Sanity: extract_jti still works after device_id was added to access tokens."""
    token = create_refresh_token("user-1")
    assert extract_jti(token) is not None
