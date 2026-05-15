"""Tests for POST /v1/auth/register."""

from collections.abc import Iterator
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from com.qode.qrew.v1.service.core.captcha import CaptchaError
from com.qode.qrew.v1.service.main import app
from com.qode.qrew.v1.service.routers.auth import get_registration_service
from com.qode.qrew.v1.service.schemas.auth import RegisterResponse
from com.qode.qrew.v1.service.services.registration import RegistrationError

_VALID_PAYLOAD: dict[str, object] = {
    "email": "alice@example.com",
    "phone_number": "+34612345678",
    "full_name": "Alice Smith",
    "password": "Str0ng!P@ssw0rd#2024",
    "terms_accepted": True,
    "captcha_token": "stub-token",
}

_ENDPOINT = "/v1/auth/register"


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_service() -> AsyncMock:
    service = AsyncMock()
    service.register = AsyncMock()
    return service


@pytest.fixture(autouse=True)
def override_service(mock_service: AsyncMock) -> Iterator[None]:
    app.dependency_overrides[get_registration_service] = lambda: mock_service
    yield
    app.dependency_overrides.clear()


# ── Happy path ────────────────────────────────────────────────────────────────


async def test_register_returns_201_with_user_id(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    mock_service.register.return_value = RegisterResponse(
        id="11111111-1111-1111-1111-111111111111",
        message="Registration successful. Check your email to verify your account.",
    )

    response = await client.post(_ENDPOINT, json=_VALID_PAYLOAD)

    assert response.status_code == 201
    body = response.json()
    assert body["id"] == "11111111-1111-1111-1111-111111111111"
    assert "email" in body["message"].lower()


async def test_register_calls_service_with_correct_args(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    mock_service.register.return_value = RegisterResponse(
        id="22222222-2222-2222-2222-222222222222",
        message="Registration successful. Check your email to verify your account.",
    )

    await client.post(_ENDPOINT, json=_VALID_PAYLOAD)

    mock_service.register.assert_awaited_once()
    call_args = mock_service.register.call_args
    request_body = call_args[0][0]
    assert request_body.email == "alice@example.com"
    assert request_body.full_name == "Alice Smith"
    assert request_body.captcha_token == "stub-token"


# ── Input validation (422) ────────────────────────────────────────────────────


async def test_rejects_missing_captcha_token(client: AsyncClient) -> None:
    payload = {k: v for k, v in _VALID_PAYLOAD.items() if k != "captcha_token"}
    response = await client.post(_ENDPOINT, json=payload)
    assert response.status_code == 422


async def test_rejects_disposable_email(client: AsyncClient) -> None:
    response = await client.post(
        _ENDPOINT, json={**_VALID_PAYLOAD, "email": "user@mailinator.com"}
    )
    assert response.status_code == 422
    assert any("disposable" in str(e).lower() for e in response.json()["detail"])


async def test_rejects_password_too_short(client: AsyncClient) -> None:
    response = await client.post(
        _ENDPOINT, json={**_VALID_PAYLOAD, "password": "Short1!"}
    )
    assert response.status_code == 422


async def test_rejects_weak_password(client: AsyncClient) -> None:
    response = await client.post(
        _ENDPOINT, json={**_VALID_PAYLOAD, "password": "password123"}
    )
    assert response.status_code == 422


async def test_rejects_terms_not_accepted(client: AsyncClient) -> None:
    response = await client.post(
        _ENDPOINT, json={**_VALID_PAYLOAD, "terms_accepted": False}
    )
    assert response.status_code == 422
    assert any("terms" in str(e).lower() for e in response.json()["detail"])


async def test_rejects_invalid_phone_number(client: AsyncClient) -> None:
    response = await client.post(
        _ENDPOINT, json={**_VALID_PAYLOAD, "phone_number": "not-a-phone!!!"}
    )
    assert response.status_code == 422


async def test_rejects_missing_required_fields(client: AsyncClient) -> None:
    response = await client.post(_ENDPOINT, json={})
    assert response.status_code == 422


# ── Business rule conflicts (409) ─────────────────────────────────────────────


async def test_returns_409_on_duplicate_email(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    mock_service.register.side_effect = RegistrationError(
        "email already registered", field="email"
    )
    response = await client.post(_ENDPOINT, json=_VALID_PAYLOAD)
    assert response.status_code == 409
    assert response.json()["detail"]["field"] == "email"


async def test_returns_409_on_duplicate_phone(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    mock_service.register.side_effect = RegistrationError(
        "phone number already registered", field="phone_number"
    )
    response = await client.post(_ENDPOINT, json=_VALID_PAYLOAD)
    assert response.status_code == 409
    assert response.json()["detail"]["field"] == "phone_number"


async def test_returns_409_on_breached_password(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    mock_service.register.side_effect = RegistrationError(
        "this password has appeared in a known data breach", field="password"
    )
    response = await client.post(_ENDPOINT, json=_VALID_PAYLOAD)
    assert response.status_code == 409
    assert response.json()["detail"]["field"] == "password"


# ── CAPTCHA failure (400) ─────────────────────────────────────────────────────


async def test_returns_400_on_captcha_failure(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    mock_service.register.side_effect = CaptchaError(
        "CAPTCHA verification failed", field="captcha_token"
    )
    response = await client.post(_ENDPOINT, json=_VALID_PAYLOAD)
    assert response.status_code == 400
    assert response.json()["detail"]["field"] == "captcha_token"
