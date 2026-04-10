"""Tests for POST /v1/auth/verify-email."""

from collections.abc import Iterator
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from com.qode.qrew.v1.service.main import app
from com.qode.qrew.v1.service.routers.auth import get_email_verification_service
from com.qode.qrew.v1.service.services.verification import VerificationError

_ENDPOINT = "/v1/auth/verify-email"
_VALID_TOKEN = "a" * 43  # realistic token length (secrets.token_urlsafe(32))


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_service() -> AsyncMock:
    service = AsyncMock()
    service.verify = AsyncMock(return_value=None)
    return service


@pytest.fixture(autouse=True)
def override_service(mock_service: AsyncMock) -> Iterator[None]:
    app.dependency_overrides[get_email_verification_service] = lambda: mock_service
    yield
    app.dependency_overrides.clear()


# ── Happy path ────────────────────────────────────────────────────────────────


async def test_verify_email_returns_200(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    response = await client.post(_ENDPOINT, json={"token": _VALID_TOKEN})

    assert response.status_code == 200
    assert "verified" in response.json()["message"].lower()
    mock_service.verify.assert_awaited_once_with(_VALID_TOKEN)


# ── Verification failures (400) ───────────────────────────────────────────────


async def test_returns_400_on_invalid_token(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    mock_service.verify.side_effect = VerificationError(
        "invalid or expired verification link", field="token"
    )
    response = await client.post(_ENDPOINT, json={"token": "bad-token"})

    assert response.status_code == 400
    assert response.json()["detail"]["field"] == "token"


async def test_returns_400_on_expired_token(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    mock_service.verify.side_effect = VerificationError(
        "this verification link has expired; request a new one", field="token"
    )
    response = await client.post(_ENDPOINT, json={"token": _VALID_TOKEN})

    assert response.status_code == 400
    assert "expired" in response.json()["detail"]["message"].lower()


async def test_returns_400_on_already_verified(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    mock_service.verify.side_effect = VerificationError(
        "this email address is already verified", field="token"
    )
    response = await client.post(_ENDPOINT, json={"token": _VALID_TOKEN})

    assert response.status_code == 400
    assert "already" in response.json()["detail"]["message"].lower()


# ── Input validation (422) ────────────────────────────────────────────────────


async def test_rejects_missing_token(client: AsyncClient) -> None:
    response = await client.post(_ENDPOINT, json={})
    assert response.status_code == 422


async def test_rejects_empty_token(client: AsyncClient) -> None:
    response = await client.post(_ENDPOINT, json={"token": ""})
    assert response.status_code == 422
