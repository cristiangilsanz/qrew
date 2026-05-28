"""Tests for all POST /v1/auth/passkey/* endpoints."""

import json
from collections.abc import Iterator
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from com.qode.qrew.v1.service.core.auth.auth import get_setup_or_full_user
from com.qode.qrew.v1.service.main import app
from com.qode.qrew.v1.service.routers.auth import (
    get_passkey_authentication_service,
    get_passkey_registration_service,
)
from com.qode.qrew.v1.service.schemas.auth.auth import LoginResponse
from com.qode.qrew.v1.service.services.passkey import PasskeyError

_REGISTER_BEGIN_ENDPOINT = "/v1/auth/passkey/register/begin"
_REGISTER_COMPLETE_ENDPOINT = "/v1/auth/passkey/register/complete"
_AUTH_BEGIN_ENDPOINT = "/v1/auth/passkey/authenticate/begin"
_AUTH_COMPLETE_ENDPOINT = "/v1/auth/passkey/authenticate/complete"

_REGISTER_PAYLOAD: dict[str, object] = {
    "id": "Y2hlY2tNZQ",
    "rawId": "Y2hlY2tNZQ",
    "response": {
        "clientDataJSON": "eyJ0eXBlIjoid2ViYXV0aG4uY3JlYXRlIn0",
        "attestationObject": "o2NmbXRkbm9uZWdhdHRTdG10oGhhdXRoRGF0YVik",
    },
    "type": "public-key",
}

_AUTH_BEGIN_PAYLOAD: dict[str, object] = {"email": "alice@example.com"}

_AUTH_COMPLETE_PAYLOAD: dict[str, object] = {
    "id": "Y2hlY2tNZQ",
    "rawId": "Y2hlY2tNZQ",
    "response": {
        "clientDataJSON": "eyJ0eXBlIjoid2ViYXV0aG4uZ2V0In0",
        "authenticatorData": "SZYN5YgOjGh0NBcPZHZgW4_krrmihjLHmVzzuoMdl2MFAAAABA",
        "signature": "MEYCIQDy0K2sGzrq7yGnxUBRyqvOBf5eRaKqMSuTvp6r1j8HqQ",
    },
    "type": "public-key",
}

_FAKE_REGISTER_OPTIONS = json.dumps(
    {
        "rp": {"name": "Qrew", "id": "localhost"},
        "user": {"id": "dXNlcklk", "name": "alice@example.com", "displayName": "Alice"},
        "challenge": "Y2hhbGxlbmdl",
        "pubKeyCredParams": [{"type": "public-key", "alg": -7}],
        "timeout": 60000,
        "attestation": "none",
    }
)

_FAKE_AUTH_OPTIONS = json.dumps(
    {
        "challenge": "Y2hhbGxlbmdl",
        "timeout": 60000,
        "rpId": "localhost",
        "allowCredentials": [{"id": "Y2hlY2tNZQ", "type": "public-key"}],
        "userVerification": "required",
    }
)


def _mock_user() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_registration_service() -> AsyncMock:
    service = AsyncMock()
    service.begin = AsyncMock(return_value=_FAKE_REGISTER_OPTIONS)
    service.complete = AsyncMock(return_value=None)
    return service


@pytest.fixture
def mock_authentication_service() -> AsyncMock:
    service = AsyncMock()
    service.begin = AsyncMock(return_value=_FAKE_AUTH_OPTIONS)
    service.complete = AsyncMock(
        return_value=LoginResponse(
            access_token="full.access.token",
            refresh_token="full.refresh.token",
        )
    )
    return service


@pytest.fixture(autouse=True)
def override_dependencies(
    mock_registration_service: AsyncMock,
    mock_authentication_service: AsyncMock,
) -> Iterator[None]:
    app.dependency_overrides[get_passkey_registration_service] = lambda: (
        mock_registration_service
    )
    app.dependency_overrides[get_passkey_authentication_service] = lambda: (
        mock_authentication_service
    )
    app.dependency_overrides[get_setup_or_full_user] = _mock_user
    yield
    app.dependency_overrides.clear()


async def test_register_begin_returns_200_with_options(
    client: AsyncClient, mock_registration_service: AsyncMock
) -> None:
    response = await client.post(_REGISTER_BEGIN_ENDPOINT)

    assert response.status_code == 200
    body = response.json()
    assert body["rp"]["name"] == "Qrew"
    assert "challenge" in body


async def test_register_begin_calls_service_with_current_user(
    client: AsyncClient, mock_registration_service: AsyncMock
) -> None:
    await client.post(_REGISTER_BEGIN_ENDPOINT)

    mock_registration_service.begin.assert_awaited_once()


async def test_register_complete_returns_200(
    client: AsyncClient, mock_registration_service: AsyncMock
) -> None:
    response = await client.post(_REGISTER_COMPLETE_ENDPOINT, json=_REGISTER_PAYLOAD)

    assert response.status_code == 200
    assert "registered" in response.json()["message"].lower()


async def test_register_complete_calls_service_with_credential(
    client: AsyncClient, mock_registration_service: AsyncMock
) -> None:
    await client.post(_REGISTER_COMPLETE_ENDPOINT, json=_REGISTER_PAYLOAD)

    mock_registration_service.complete.assert_awaited_once()


async def test_register_complete_returns_400_on_expired_challenge(
    client: AsyncClient, mock_registration_service: AsyncMock
) -> None:
    mock_registration_service.complete.side_effect = PasskeyError(
        "Registration session expired. Please start again."
    )

    response = await client.post(_REGISTER_COMPLETE_ENDPOINT, json=_REGISTER_PAYLOAD)

    assert response.status_code == 400


async def test_register_complete_returns_400_on_verification_failure(
    client: AsyncClient, mock_registration_service: AsyncMock
) -> None:
    mock_registration_service.complete.side_effect = PasskeyError(
        "Passkey registration failed. Please try again."
    )

    response = await client.post(_REGISTER_COMPLETE_ENDPOINT, json=_REGISTER_PAYLOAD)

    assert response.status_code == 400


async def test_register_complete_rejects_missing_id(client: AsyncClient) -> None:
    payload = {k: v for k, v in _REGISTER_PAYLOAD.items() if k != "id"}

    response = await client.post(_REGISTER_COMPLETE_ENDPOINT, json=payload)

    assert response.status_code == 422


async def test_register_complete_rejects_missing_response(client: AsyncClient) -> None:
    payload = {k: v for k, v in _REGISTER_PAYLOAD.items() if k != "response"}

    response = await client.post(_REGISTER_COMPLETE_ENDPOINT, json=payload)

    assert response.status_code == 422


async def test_auth_begin_returns_200_with_assertion_options(
    client: AsyncClient, mock_authentication_service: AsyncMock
) -> None:
    response = await client.post(_AUTH_BEGIN_ENDPOINT, json=_AUTH_BEGIN_PAYLOAD)

    assert response.status_code == 200
    body = response.json()
    assert "challenge" in body
    assert body["rpId"] == "localhost"


async def test_auth_begin_calls_service_with_email(
    client: AsyncClient, mock_authentication_service: AsyncMock
) -> None:
    await client.post(_AUTH_BEGIN_ENDPOINT, json=_AUTH_BEGIN_PAYLOAD)

    mock_authentication_service.begin.assert_awaited_once_with("alice@example.com")


async def test_auth_begin_returns_400_when_no_passkey(
    client: AsyncClient, mock_authentication_service: AsyncMock
) -> None:
    mock_authentication_service.begin.side_effect = PasskeyError(
        "No passkey registered for this account"
    )

    response = await client.post(_AUTH_BEGIN_ENDPOINT, json=_AUTH_BEGIN_PAYLOAD)

    assert response.status_code == 400


async def test_auth_begin_rejects_invalid_email(client: AsyncClient) -> None:
    response = await client.post(_AUTH_BEGIN_ENDPOINT, json={"email": "not-an-email"})

    assert response.status_code == 422


async def test_auth_complete_returns_200_with_full_tokens(
    client: AsyncClient, mock_authentication_service: AsyncMock
) -> None:
    response = await client.post(_AUTH_COMPLETE_ENDPOINT, json=_AUTH_COMPLETE_PAYLOAD)

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"] == "full.access.token"
    assert body["refresh_token"] == "full.refresh.token"
    assert body["setup_required"] is False


async def test_auth_complete_returns_200_with_setup_token_when_incomplete(
    client: AsyncClient, mock_authentication_service: AsyncMock
) -> None:
    mock_authentication_service.complete.return_value = LoginResponse(
        access_token="setup.token",
        setup_required=True,
    )

    response = await client.post(_AUTH_COMPLETE_ENDPOINT, json=_AUTH_COMPLETE_PAYLOAD)

    assert response.status_code == 200
    body = response.json()
    assert body["setup_required"] is True
    assert body["refresh_token"] is None


async def test_auth_complete_calls_service_with_assertion(
    client: AsyncClient, mock_authentication_service: AsyncMock
) -> None:
    await client.post(_AUTH_COMPLETE_ENDPOINT, json=_AUTH_COMPLETE_PAYLOAD)

    mock_authentication_service.complete.assert_awaited_once()


async def test_auth_complete_returns_400_on_expired_session(
    client: AsyncClient, mock_authentication_service: AsyncMock
) -> None:
    mock_authentication_service.complete.side_effect = PasskeyError(
        "Authentication session expired. Please start again."
    )

    response = await client.post(_AUTH_COMPLETE_ENDPOINT, json=_AUTH_COMPLETE_PAYLOAD)

    assert response.status_code == 400


async def test_auth_complete_returns_400_on_verification_failure(
    client: AsyncClient, mock_authentication_service: AsyncMock
) -> None:
    mock_authentication_service.complete.side_effect = PasskeyError(
        "Passkey authentication failed. Please try again."
    )

    response = await client.post(_AUTH_COMPLETE_ENDPOINT, json=_AUTH_COMPLETE_PAYLOAD)

    assert response.status_code == 400


async def test_auth_complete_rejects_missing_id(client: AsyncClient) -> None:
    payload = {k: v for k, v in _AUTH_COMPLETE_PAYLOAD.items() if k != "id"}

    response = await client.post(_AUTH_COMPLETE_ENDPOINT, json=payload)

    assert response.status_code == 422


async def test_auth_complete_rejects_missing_response(client: AsyncClient) -> None:
    payload = {k: v for k, v in _AUTH_COMPLETE_PAYLOAD.items() if k != "response"}

    response = await client.post(_AUTH_COMPLETE_ENDPOINT, json=payload)

    assert response.status_code == 422
