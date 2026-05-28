"""Tests for profile and onboarding-status endpoints:
GET /v1/auth/me
GET /v1/auth/onboarding-status
"""

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from com.qode.qrew.v1.service.core.auth.auth import (
    get_current_user,
    get_setup_or_full_user,
)
from com.qode.qrew.v1.service.main import app
from com.qode.qrew.v1.service.models.auth.user import KycStatus

_ME_ENDPOINT = "/v1/auth/me"
_ONBOARDING_ENDPOINT = "/v1/auth/onboarding-status"

_PASSKEY_REPO = (
    "com.qode.qrew.v1.service.routers.auth.profile.PasskeyCredentialRepository"
)


def _mock_user(
    email_verified: bool = True,
    phone_verified: bool = True,
    kyc_status: KycStatus = KycStatus.approved,
) -> MagicMock:
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = "user@example.com"
    user.full_name = "Test User"
    user.phone_number = "+34612345678"
    user.kyc_status = kyc_status
    user.email_verified = email_verified
    user.phone_number_verified = phone_verified
    user.created_at = datetime(2026, 1, 1, tzinfo=UTC)
    return user


@pytest.fixture(autouse=True)
def override_user() -> Iterator[None]:
    app.dependency_overrides[get_current_user] = _mock_user
    app.dependency_overrides[get_setup_or_full_user] = _mock_user
    yield
    app.dependency_overrides.clear()


async def test_me_returns_200_with_profile(client: AsyncClient) -> None:
    response = await client.get(_ME_ENDPOINT)

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "user@example.com"
    assert body["full_name"] == "Test User"
    assert body["phone_number"] == "+34612345678"
    assert body["kyc_status"] == KycStatus.approved
    assert body["email_verified"] is True
    assert body["phone_verified"] is True
    assert "id" in body
    assert "created_at" in body


async def test_me_requires_auth(client: AsyncClient) -> None:
    app.dependency_overrides.pop(get_current_user, None)

    response = await client.get(_ME_ENDPOINT)

    assert response.status_code == 401


async def test_onboarding_status_all_complete(client: AsyncClient) -> None:
    with patch(_PASSKEY_REPO) as mock_repo_cls:
        mock_repo_cls.return_value.has_passkey = AsyncMock(return_value=True)

        response = await client.get(_ONBOARDING_ENDPOINT)

    assert response.status_code == 200
    body = response.json()
    assert body["email_verified"] is True
    assert body["phone_verified"] is True
    assert body["kyc_submitted"] is True
    assert body["passkey_registered"] is True
    assert body["is_complete"] is True


async def test_onboarding_status_no_passkey(client: AsyncClient) -> None:
    with patch(_PASSKEY_REPO) as mock_repo_cls:
        mock_repo_cls.return_value.has_passkey = AsyncMock(return_value=False)

        response = await client.get(_ONBOARDING_ENDPOINT)

    assert response.status_code == 200
    body = response.json()
    assert body["passkey_registered"] is False
    assert body["is_complete"] is False


async def test_onboarding_status_kyc_not_submitted(client: AsyncClient) -> None:
    app.dependency_overrides[get_setup_or_full_user] = lambda: _mock_user(
        kyc_status=KycStatus.not_submitted
    )

    with patch(_PASSKEY_REPO) as mock_repo_cls:
        mock_repo_cls.return_value.has_passkey = AsyncMock(return_value=True)

        response = await client.get(_ONBOARDING_ENDPOINT)

    assert response.status_code == 200
    body = response.json()
    assert body["kyc_submitted"] is False
    assert body["is_complete"] is False


async def test_onboarding_status_email_not_verified(client: AsyncClient) -> None:
    app.dependency_overrides[get_setup_or_full_user] = lambda: _mock_user(
        email_verified=False
    )

    with patch(_PASSKEY_REPO) as mock_repo_cls:
        mock_repo_cls.return_value.has_passkey = AsyncMock(return_value=True)

        response = await client.get(_ONBOARDING_ENDPOINT)

    assert response.status_code == 200
    body = response.json()
    assert body["email_verified"] is False
    assert body["is_complete"] is False


async def test_onboarding_status_requires_setup_or_full_token(
    client: AsyncClient,
) -> None:
    app.dependency_overrides.pop(get_setup_or_full_user, None)

    response = await client.get(_ONBOARDING_ENDPOINT)

    assert response.status_code == 401
