"""Tests for POST /v1/auth/verify-phone."""

from collections.abc import Iterator
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from com.qode.qrew.v1.service.main import app
from com.qode.qrew.v1.service.routers.auth import get_phone_verification_service
from com.qode.qrew.v1.service.services.verification import VerificationError

_ENDPOINT = "/v1/auth/verify-phone"
_VALID_PAYLOAD: dict[str, str] = {
    "phone_number": "+34612345678",
    "otp": "482910",
}


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_service() -> AsyncMock:
    service = AsyncMock()
    service.verify = AsyncMock(return_value=None)
    return service


@pytest.fixture(autouse=True)
def override_service(mock_service: AsyncMock) -> Iterator[None]:
    app.dependency_overrides[get_phone_verification_service] = lambda: mock_service
    yield
    app.dependency_overrides.clear()


# ── Happy path ────────────────────────────────────────────────────────────────


async def test_verify_phone_returns_200(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    response = await client.post(_ENDPOINT, json=_VALID_PAYLOAD)

    assert response.status_code == 200
    assert "verified" in response.json()["message"].lower()
    mock_service.verify.assert_awaited_once_with(
        _VALID_PAYLOAD["phone_number"], _VALID_PAYLOAD["otp"]
    )


# ── Verification failures (400) ───────────────────────────────────────────────


async def test_returns_400_on_invalid_otp(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    mock_service.verify.side_effect = VerificationError(
        "invalid or expired OTP", field="otp"
    )
    response = await client.post(_ENDPOINT, json=_VALID_PAYLOAD)

    assert response.status_code == 400
    assert response.json()["detail"]["field"] == "otp"


async def test_returns_400_on_expired_otp(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    mock_service.verify.side_effect = VerificationError(
        "this OTP has expired; request a new one", field="otp"
    )
    response = await client.post(_ENDPOINT, json=_VALID_PAYLOAD)

    assert response.status_code == 400
    assert "expired" in response.json()["detail"]["message"].lower()


async def test_returns_400_on_already_verified(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    mock_service.verify.side_effect = VerificationError(
        "this phone number is already verified", field="otp"
    )
    response = await client.post(_ENDPOINT, json=_VALID_PAYLOAD)

    assert response.status_code == 400
    assert "already" in response.json()["detail"]["message"].lower()


# ── Input validation (422) ────────────────────────────────────────────────────


async def test_rejects_non_digit_otp(client: AsyncClient) -> None:
    response = await client.post(_ENDPOINT, json={**_VALID_PAYLOAD, "otp": "abcdef"})
    assert response.status_code == 422


async def test_rejects_otp_wrong_length(client: AsyncClient) -> None:
    response = await client.post(_ENDPOINT, json={**_VALID_PAYLOAD, "otp": "12345"})
    assert response.status_code == 422


async def test_rejects_invalid_phone_format(client: AsyncClient) -> None:
    response = await client.post(
        _ENDPOINT, json={**_VALID_PAYLOAD, "phone_number": "not-a-phone!!!"}
    )
    assert response.status_code == 422


async def test_rejects_missing_required_fields(client: AsyncClient) -> None:
    response = await client.post(_ENDPOINT, json={})
    assert response.status_code == 422
