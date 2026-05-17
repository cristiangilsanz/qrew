"""Tests for POST /v1/auth/passkey/authenticate/begin and /complete."""

import json
from collections.abc import Iterator
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from com.qode.qrew.v1.service.main import app
from com.qode.qrew.v1.service.routers.auth import get_passkey_service
from com.qode.qrew.v1.service.schemas.auth import LoginResponse
from com.qode.qrew.v1.service.services.passkey import PasskeyError

_BEGIN_ENDPOINT = "/v1/auth/passkey/authenticate/begin"
_COMPLETE_ENDPOINT = "/v1/auth/passkey/authenticate/complete"

_VALID_BEGIN_PAYLOAD: dict[str, object] = {"email": "alice@example.com"}

_VALID_COMPLETE_PAYLOAD: dict[str, object] = {
    "id": "Y2hlY2tNZQ",
    "rawId": "Y2hlY2tNZQ",
    "response": {
        "clientDataJSON": "eyJ0eXBlIjoid2ViYXV0aG4uZ2V0In0",
        "authenticatorData": "SZYN5YgOjGh0NBcPZHZgW4_krrmihjLHmVzzuoMdl2MFAAAABA",
        "signature": "MEYCIQDy0K2sGzrq7yGnxUBRyqvOBf5eRaKqMSuTvp6r1j8HqQ",
    },
    "type": "public-key",
}

_FAKE_ASSERT_OPTIONS = json.dumps(
    {
        "challenge": "Y2hhbGxlbmdl",
        "timeout": 60000,
        "rpId": "localhost",
        "allowCredentials": [{"id": "Y2hlY2tNZQ", "type": "public-key"}],
        "userVerification": "required",
    }
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_service() -> AsyncMock:
    service = AsyncMock()
    service.begin_authentication = AsyncMock(return_value=_FAKE_ASSERT_OPTIONS)
    service.complete_authentication = AsyncMock(
        return_value=LoginResponse(
            access_token="full.access.token",
            refresh_token="full.refresh.token",
        )
    )
    return service


@pytest.fixture(autouse=True)
def override_dependencies(mock_service: AsyncMock) -> Iterator[None]:
    app.dependency_overrides[get_passkey_service] = lambda: mock_service
    yield
    app.dependency_overrides.clear()


# ── begin ─────────────────────────────────────────────────────────────────────


async def test_begin_returns_200_with_assertion_options(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    response = await client.post(_BEGIN_ENDPOINT, json=_VALID_BEGIN_PAYLOAD)

    assert response.status_code == 200
    body = response.json()
    assert "challenge" in body
    assert body["rpId"] == "localhost"


async def test_begin_calls_service_with_email(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    await client.post(_BEGIN_ENDPOINT, json=_VALID_BEGIN_PAYLOAD)
    mock_service.begin_authentication.assert_awaited_once_with("alice@example.com")


async def test_begin_returns_400_when_no_passkey(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    mock_service.begin_authentication.side_effect = PasskeyError(
        "No passkey registered for this account"
    )
    response = await client.post(_BEGIN_ENDPOINT, json=_VALID_BEGIN_PAYLOAD)
    assert response.status_code == 400


async def test_begin_rejects_invalid_email(client: AsyncClient) -> None:
    response = await client.post(_BEGIN_ENDPOINT, json={"email": "not-an-email"})
    assert response.status_code == 422


# ── complete ──────────────────────────────────────────────────────────────────


async def test_complete_returns_200_with_full_tokens(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    response = await client.post(_COMPLETE_ENDPOINT, json=_VALID_COMPLETE_PAYLOAD)

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"] == "full.access.token"
    assert body["refresh_token"] == "full.refresh.token"
    assert body["setup_required"] is False


async def test_complete_returns_200_with_setup_token_when_incomplete(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    mock_service.complete_authentication.return_value = LoginResponse(
        access_token="setup.token",
        setup_required=True,
    )
    response = await client.post(_COMPLETE_ENDPOINT, json=_VALID_COMPLETE_PAYLOAD)

    assert response.status_code == 200
    body = response.json()
    assert body["setup_required"] is True
    assert body["refresh_token"] is None


async def test_complete_calls_service_with_assertion(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    await client.post(_COMPLETE_ENDPOINT, json=_VALID_COMPLETE_PAYLOAD)
    mock_service.complete_authentication.assert_awaited_once()


async def test_complete_returns_400_on_expired_session(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    mock_service.complete_authentication.side_effect = PasskeyError(
        "Authentication session expired. Please start again."
    )
    response = await client.post(_COMPLETE_ENDPOINT, json=_VALID_COMPLETE_PAYLOAD)
    assert response.status_code == 400


async def test_complete_returns_400_on_verification_failure(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    mock_service.complete_authentication.side_effect = PasskeyError(
        "Passkey authentication failed. Please try again."
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
