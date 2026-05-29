"""Tests for account-recovery endpoints:
POST /v1/auth/recovery/begin
POST /v1/auth/recovery/complete
"""

import uuid
from collections.abc import Iterator
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from com.qode.qrew.v1.service.core.auth.auth import get_recovery_user
from com.qode.qrew.v1.service.main import app
from com.qode.qrew.v1.service.routers.auth import get_recovery_service
from com.qode.qrew.v1.service.services.account.recovery import RecoveryError

_BEGIN_ENDPOINT = "/v1/auth/recovery/begin"
_COMPLETE_ENDPOINT = "/v1/auth/recovery/complete"

_FAKE_DOCUMENT = b"fake-national-id-document"
_FAKE_EMAIL = "user@example.com"
_FAKE_RECOVERY_TOKEN = "recovery.jwt.token"
_FAKE_PASSKEY_OPTIONS = '{"challenge":"abc123"}'

_COMPLETE_BODY = {
    "id": "credential-id",
    "rawId": "cmF3LWlk",
    "response": {
        "clientDataJSON": "Y2xpZW50LWRhdGE=",
        "attestationObject": "YXR0ZXN0YXRpb24=",
    },
    "type": "public-key",
}


def _mock_user() -> MagicMock:
    user = MagicMock()
    user.id = uuid.uuid4()
    return user


@pytest.fixture
def mock_service() -> AsyncMock:
    service = AsyncMock()
    service.begin = AsyncMock(
        return_value=(_FAKE_RECOVERY_TOKEN, _FAKE_PASSKEY_OPTIONS)
    )
    service.complete = AsyncMock(return_value=None)
    return service


@pytest.fixture(autouse=True)
def override_dependencies(mock_service: AsyncMock) -> Iterator[None]:
    app.dependency_overrides[get_recovery_service] = lambda: mock_service
    app.dependency_overrides[get_recovery_user] = _mock_user
    yield
    app.dependency_overrides.clear()


async def test_begin_returns_200_with_token(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    response = await client.post(
        _BEGIN_ENDPOINT,
        data={"email": _FAKE_EMAIL},
        files={"document": ("id.jpg", _FAKE_DOCUMENT, "image/jpeg")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["recovery_token"] == _FAKE_RECOVERY_TOKEN
    assert body["passkey_options"] == _FAKE_PASSKEY_OPTIONS


async def test_begin_calls_service_with_email_and_content(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    await client.post(
        _BEGIN_ENDPOINT,
        data={"email": _FAKE_EMAIL},
        files={"document": ("id.jpg", _FAKE_DOCUMENT, "image/jpeg")},
    )

    mock_service.begin.assert_awaited_once_with(_FAKE_EMAIL, _FAKE_DOCUMENT)


async def test_begin_returns_200_with_no_token_when_no_match(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    mock_service.begin = AsyncMock(return_value=(None, ""))

    response = await client.post(
        _BEGIN_ENDPOINT,
        data={"email": _FAKE_EMAIL},
        files={"document": ("id.jpg", _FAKE_DOCUMENT, "image/jpeg")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["recovery_token"] is None
    assert body["passkey_options"] is None
    assert "matching account" in body["message"]


async def test_begin_requires_email_field(client: AsyncClient) -> None:
    response = await client.post(
        _BEGIN_ENDPOINT,
        files={"document": ("id.jpg", _FAKE_DOCUMENT, "image/jpeg")},
    )

    assert response.status_code == 422


async def test_begin_requires_document_field(client: AsyncClient) -> None:
    response = await client.post(
        _BEGIN_ENDPOINT,
        data={"email": _FAKE_EMAIL},
    )

    assert response.status_code == 422


async def test_complete_returns_200(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    response = await client.post(_COMPLETE_ENDPOINT, json=_COMPLETE_BODY)

    assert response.status_code == 200
    assert "complete" in response.json()["message"].lower()


async def test_complete_calls_service(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    await client.post(_COMPLETE_ENDPOINT, json=_COMPLETE_BODY)

    mock_service.complete.assert_awaited_once()


async def test_complete_returns_400_on_recovery_error(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    mock_service.complete = AsyncMock(
        side_effect=RecoveryError("Recovery session expired. Please start again.")
    )

    response = await client.post(_COMPLETE_ENDPOINT, json=_COMPLETE_BODY)

    assert response.status_code == 400
    assert "expired" in response.json()["detail"]["message"]


async def test_complete_requires_recovery_token(client: AsyncClient) -> None:
    app.dependency_overrides.pop(get_recovery_user, None)

    response = await client.post(_COMPLETE_ENDPOINT, json=_COMPLETE_BODY)

    assert response.status_code == 401
