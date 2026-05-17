"""Tests for POST /v1/auth/resend-email-verification and /v1/auth/resend-phone-otp."""

from collections.abc import Iterator
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from com.qode.qrew.v1.service.main import app
from com.qode.qrew.v1.service.routers.auth import (
    get_resend_email_verification_service,
    get_resend_phone_otp_service,
)
from com.qode.qrew.v1.service.services.resend_verification import ResendError

_EMAIL_ENDPOINT = "/v1/auth/resend-email-verification"
_PHONE_ENDPOINT = "/v1/auth/resend-phone-otp"

_VALID_EMAIL_PAYLOAD: dict[str, object] = {"email": "alice@example.com"}
_VALID_PHONE_PAYLOAD: dict[str, object] = {"phone_number": "+34612345678"}


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_email_service() -> AsyncMock:
    service = AsyncMock()
    service.resend = AsyncMock()
    return service


@pytest.fixture
def mock_phone_service() -> AsyncMock:
    service = AsyncMock()
    service.resend = AsyncMock()
    return service


@pytest.fixture(autouse=True)
def override_dependencies(
    mock_email_service: AsyncMock, mock_phone_service: AsyncMock
) -> Iterator[None]:
    app.dependency_overrides[get_resend_email_verification_service] = lambda: (
        mock_email_service
    )
    app.dependency_overrides[get_resend_phone_otp_service] = lambda: mock_phone_service
    yield
    app.dependency_overrides.clear()


# ── resend-email-verification ─────────────────────────────────────────────────


async def test_resend_email_returns_200(
    client: AsyncClient, mock_email_service: AsyncMock
) -> None:
    mock_email_service.resend.return_value = None

    response = await client.post(_EMAIL_ENDPOINT, json=_VALID_EMAIL_PAYLOAD)

    assert response.status_code == 200
    assert "message" in response.json()


async def test_resend_email_calls_service_with_email(
    client: AsyncClient, mock_email_service: AsyncMock
) -> None:
    mock_email_service.resend.return_value = None

    await client.post(_EMAIL_ENDPOINT, json=_VALID_EMAIL_PAYLOAD)

    mock_email_service.resend.assert_awaited_once_with("alice@example.com")


async def test_resend_email_rejects_missing_email(client: AsyncClient) -> None:
    response = await client.post(_EMAIL_ENDPOINT, json={})
    assert response.status_code == 422


async def test_resend_email_rejects_invalid_email_format(client: AsyncClient) -> None:
    response = await client.post(_EMAIL_ENDPOINT, json={"email": "not-an-email"})
    assert response.status_code == 422


async def test_resend_email_returns_400_when_user_not_found(
    client: AsyncClient, mock_email_service: AsyncMock
) -> None:
    mock_email_service.resend.side_effect = ResendError(
        "No account found with that email address", field="email"
    )
    response = await client.post(_EMAIL_ENDPOINT, json=_VALID_EMAIL_PAYLOAD)
    assert response.status_code == 400


async def test_resend_email_returns_400_when_already_verified(
    client: AsyncClient, mock_email_service: AsyncMock
) -> None:
    mock_email_service.resend.side_effect = ResendError(
        "This email address is already verified", field="email"
    )
    response = await client.post(_EMAIL_ENDPOINT, json=_VALID_EMAIL_PAYLOAD)
    assert response.status_code == 400


async def test_resend_email_error_includes_field(
    client: AsyncClient, mock_email_service: AsyncMock
) -> None:
    mock_email_service.resend.side_effect = ResendError(
        "This email address is already verified", field="email"
    )
    response = await client.post(_EMAIL_ENDPOINT, json=_VALID_EMAIL_PAYLOAD)
    assert response.json()["detail"]["field"] == "email"


# ── resend-phone-otp ──────────────────────────────────────────────────────────


async def test_resend_phone_returns_200(
    client: AsyncClient, mock_phone_service: AsyncMock
) -> None:
    mock_phone_service.resend.return_value = None

    response = await client.post(_PHONE_ENDPOINT, json=_VALID_PHONE_PAYLOAD)

    assert response.status_code == 200
    assert "message" in response.json()


async def test_resend_phone_calls_service_with_phone_number(
    client: AsyncClient, mock_phone_service: AsyncMock
) -> None:
    mock_phone_service.resend.return_value = None

    await client.post(_PHONE_ENDPOINT, json=_VALID_PHONE_PAYLOAD)

    mock_phone_service.resend.assert_awaited_once_with("+34612345678")


async def test_resend_phone_rejects_missing_phone(client: AsyncClient) -> None:
    response = await client.post(_PHONE_ENDPOINT, json={})
    assert response.status_code == 422


async def test_resend_phone_rejects_invalid_phone_format(client: AsyncClient) -> None:
    response = await client.post(_PHONE_ENDPOINT, json={"phone_number": "not-a-phone"})
    assert response.status_code == 422


async def test_resend_phone_returns_400_when_user_not_found(
    client: AsyncClient, mock_phone_service: AsyncMock
) -> None:
    mock_phone_service.resend.side_effect = ResendError(
        "No account found with that phone number", field="phone_number"
    )
    response = await client.post(_PHONE_ENDPOINT, json=_VALID_PHONE_PAYLOAD)
    assert response.status_code == 400


async def test_resend_phone_returns_400_when_already_verified(
    client: AsyncClient, mock_phone_service: AsyncMock
) -> None:
    mock_phone_service.resend.side_effect = ResendError(
        "This phone number is already verified", field="phone_number"
    )
    response = await client.post(_PHONE_ENDPOINT, json=_VALID_PHONE_PAYLOAD)
    assert response.status_code == 400


async def test_resend_phone_error_includes_field(
    client: AsyncClient, mock_phone_service: AsyncMock
) -> None:
    mock_phone_service.resend.side_effect = ResendError(
        "This phone number is already verified", field="phone_number"
    )
    response = await client.post(_PHONE_ENDPOINT, json=_VALID_PHONE_PAYLOAD)
    assert response.json()["detail"]["field"] == "phone_number"
