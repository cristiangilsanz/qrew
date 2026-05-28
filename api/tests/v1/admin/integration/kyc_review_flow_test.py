"""Integration tests for POST /v1/admin/kyc/{user_id}/review."""

import uuid
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.service.core.auth import pii_crypto
from com.qode.qrew.v1.service.core.auth.security import create_access_token
from com.qode.qrew.v1.service.models.auth.user import KycStatus, User

_EMAIL = "kyc-user@example.com"
_PHONE = "+34612345679"
_PASSWORD = "Tr0ub4dor&3"
_FULL_NAME = "KYC Test User"

_REGISTER_PAYLOAD: dict[str, object] = {
    "full_name": _FULL_NAME,
    "email": _EMAIL,
    "phone_number": _PHONE,
    "password": _PASSWORD,
    "terms_accepted": True,
    "captcha_token": "test-token",
}


async def _create_pending_user(client: AsyncClient, db: AsyncSession) -> User:
    """Register, verify email, login, upload KYC."""
    r = await client.post("/v1/auth/register", json=_REGISTER_PAYLOAD)
    assert r.status_code == 201

    result = await db.execute(
        select(User).where(User.email_hash == pii_crypto.hash_lookup(_EMAIL))
    )
    user = result.scalar_one()

    r = await client.post(
        "/v1/auth/verify-email",
        json={"token": user.email_verification_token},
    )
    assert r.status_code == 200

    r = await client.post(
        "/v1/auth/login", json={"email": _EMAIL, "password": _PASSWORD}
    )
    setup_token = r.json()["access_token"]
    auth = {"Authorization": f"Bearer {setup_token}"}

    r = await client.post(
        "/v1/auth/kyc/upload",
        files={"document": ("id.jpg", b"fake-content", "image/jpeg")},
        headers=auth,
    )
    assert r.status_code == 200

    await db.refresh(user)
    assert user.kyc_status == KycStatus.pending
    return user


def _admin_auth(user: User) -> dict[str, str]:
    """Return an Authorization header with a full-access token for an admin user."""
    return {"Authorization": f"Bearer {create_access_token(str(user.id))}"}


@pytest.mark.integration
async def test_admin_can_approve_pending_kyc(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    user = await _create_pending_user(client, db_session)

    user.is_admin = True
    await db_session.commit()

    response = await client.post(
        f"/v1/admin/kyc/{user.id}/review",
        json={"action": "approve"},
        headers=_admin_auth(user),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["kyc_status"] == "approved"
    assert body["user_id"] == str(user.id)

    await db_session.refresh(user)
    assert user.kyc_status == KycStatus.approved


@pytest.mark.integration
async def test_admin_can_reject_pending_kyc_with_reason(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    user = await _create_pending_user(client, db_session)

    user.is_admin = True
    await db_session.commit()

    response = await client.post(
        f"/v1/admin/kyc/{user.id}/review",
        json={"action": "reject", "reason": "Document is not readable"},
        headers=_admin_auth(user),
    )

    assert response.status_code == 200
    assert response.json()["kyc_status"] == "rejected"

    await db_session.refresh(user)
    assert user.kyc_status == KycStatus.rejected


@pytest.mark.integration
async def test_non_admin_cannot_review_kyc(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    user = await _create_pending_user(client, db_session)

    response = await client.post(
        f"/v1/admin/kyc/{user.id}/review",
        json={"action": "approve"},
        headers=_admin_auth(user),
    )

    assert response.status_code == 403


@pytest.mark.integration
async def test_cannot_review_non_pending_kyc(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    user = await _create_pending_user(client, db_session)

    user.is_admin = True
    user.kyc_status = KycStatus.approved
    await db_session.commit()

    response = await client.post(
        f"/v1/admin/kyc/{user.id}/review",
        json={"action": "approve"},
        headers=_admin_auth(user),
    )

    assert response.status_code == 400
    assert "not pending" in response.json()["detail"]["message"].lower()


@pytest.mark.integration
async def test_returns_400_for_unknown_user(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    result = await db_session.execute(select(User).limit(1))
    existing = result.scalar_one_or_none()
    if existing is None:
        pytest.skip("needs at least one user to get an admin token")

    existing.is_admin = True
    await db_session.commit()

    fake_id = uuid.uuid4()

    response = await client.post(
        f"/v1/admin/kyc/{fake_id}/review",
        json={"action": "approve"},
        headers=_admin_auth(existing),
    )

    assert response.status_code == 400
    assert "not found" in response.json()["detail"]["message"].lower()


@pytest.mark.integration
async def test_kyc_upload_auto_approves_when_flag_enabled(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """When kyc_auto_approve is True the upload response returns approved."""
    r = await client.post("/v1/auth/register", json=_REGISTER_PAYLOAD)
    assert r.status_code == 201

    result = await db_session.execute(
        select(User).where(User.email_hash == pii_crypto.hash_lookup(_EMAIL))
    )
    user = result.scalar_one()

    r = await client.post(
        "/v1/auth/verify-email",
        json={"token": user.email_verification_token},
    )
    r = await client.post(
        "/v1/auth/login", json={"email": _EMAIL, "password": _PASSWORD}
    )
    auth = {"Authorization": f"Bearer {r.json()['access_token']}"}

    with patch("com.qode.qrew.v1.service.services.kyc.kyc.settings") as mock_settings:
        mock_settings.kyc_auto_approve = True
        mock_settings.max_file_bytes = 10 * 1024 * 1024
        mock_settings.national_id_encryption_key = (
            "c2VrcmV0c2VrcmV0c2VrcmV0c2VrcmV0c2VrcmV0c2U="
        )

        r = await client.post(
            "/v1/auth/kyc/upload",
            files={"document": ("id.jpg", b"fake-content", "image/jpeg")},
            headers=auth,
        )

    assert r.status_code == 200
    assert r.json()["kyc_status"] == "approved"

    await db_session.refresh(user)
    assert user.kyc_status == KycStatus.approved
