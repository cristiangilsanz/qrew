"""Tests for POST /v1/auth/login."""

from collections.abc import Iterator
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from com.qode.qrew.v1.service.main import app
from com.qode.qrew.v1.service.routers.auth import get_login_service
from com.qode.qrew.v1.service.schemas.auth import LoginResponse
from com.qode.qrew.v1.service.services.login import LoginError

_VALID_PAYLOAD: dict[str, object] = {
    "email": "alice@example.com",
    "password": "Str0ng!P@ssw0rd#2024",
}

_ENDPOINT = "/v1/auth/login"


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_service() -> AsyncMock:
    service = AsyncMock()
    service.login = AsyncMock()
    return service


@pytest.fixture(autouse=True)
def override_dependencies(mock_service: AsyncMock) -> Iterator[None]:
    app.dependency_overrides[get_login_service] = lambda: mock_service
    yield
    app.dependency_overrides.clear()


# ── Happy path ────────────────────────────────────────────────────────────────


async def test_login_returns_200_with_tokens(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    # Given
    mock_service.login.return_value = LoginResponse(
        access_token="a.b.c",
        refresh_token="d.e.f",
    )

    # When
    response = await client.post(_ENDPOINT, json=_VALID_PAYLOAD)

    # Then
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"] == "a.b.c"
    assert body["refresh_token"] == "d.e.f"
    assert body["token_type"] == "bearer"
    assert body["setup_required"] is False


async def test_login_returns_setup_token_when_setup_incomplete(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    # Given
    mock_service.login.return_value = LoginResponse(
        access_token="setup.token",
        setup_required=True,
    )

    # When
    response = await client.post(_ENDPOINT, json=_VALID_PAYLOAD)

    # Then
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"] == "setup.token"
    assert body["refresh_token"] is None
    assert body["setup_required"] is True


async def test_login_calls_service_with_correct_args(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    # Given
    mock_service.login.return_value = LoginResponse(
        access_token="a.b.c",
        refresh_token="d.e.f",
    )

    # When
    await client.post(_ENDPOINT, json=_VALID_PAYLOAD)

    # Then
    mock_service.login.assert_awaited_once()
    call_args = mock_service.login.call_args
    request_body = call_args[0][0]
    assert request_body.email == "alice@example.com"
    assert request_body.password == "Str0ng!P@ssw0rd#2024"


# ── Input validation (422) ────────────────────────────────────────────────────


async def test_rejects_missing_email(client: AsyncClient) -> None:
    # Given
    payload = {k: v for k, v in _VALID_PAYLOAD.items() if k != "email"}

    # When
    response = await client.post(_ENDPOINT, json=payload)

    # Then
    assert response.status_code == 422


async def test_rejects_missing_password(client: AsyncClient) -> None:
    # Given
    payload = {k: v for k, v in _VALID_PAYLOAD.items() if k != "password"}

    # When
    response = await client.post(_ENDPOINT, json=payload)

    # Then
    assert response.status_code == 422


async def test_rejects_invalid_email_format(client: AsyncClient) -> None:
    # When
    response = await client.post(
        _ENDPOINT, json={**_VALID_PAYLOAD, "email": "not-an-email"}
    )

    # Then
    assert response.status_code == 422


async def test_rejects_empty_password(client: AsyncClient) -> None:
    # When
    response = await client.post(_ENDPOINT, json={**_VALID_PAYLOAD, "password": ""})

    # Then
    assert response.status_code == 422


async def test_rejects_empty_body(client: AsyncClient) -> None:
    # When
    response = await client.post(_ENDPOINT, json={})

    # Then
    assert response.status_code == 422


# ── Authentication failures (401) ────────────────────────────────────────────


async def test_returns_401_on_invalid_credentials(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    # Given
    mock_service.login.side_effect = LoginError("Invalid email or password")

    # When
    response = await client.post(_ENDPOINT, json=_VALID_PAYLOAD)

    # Then
    assert response.status_code == 401


async def test_returns_401_on_unverified_email(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    # Given
    mock_service.login.side_effect = LoginError(
        "Please verify your email before logging in"
    )

    # When
    response = await client.post(_ENDPOINT, json=_VALID_PAYLOAD)

    # Then
    assert response.status_code == 401


async def test_returns_401_on_deactivated_account(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    # Given
    mock_service.login.side_effect = LoginError("Account has been deactivated")

    # When
    response = await client.post(_ENDPOINT, json=_VALID_PAYLOAD)

    # Then
    assert response.status_code == 401


async def test_credential_error_has_no_field(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    # Given
    mock_service.login.side_effect = LoginError("Invalid email or password")

    # When
    response = await client.post(_ENDPOINT, json=_VALID_PAYLOAD)

    # Then
    assert response.json()["detail"]["field"] is None
