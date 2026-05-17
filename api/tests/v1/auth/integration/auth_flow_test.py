"""Integration tests for the full auth verification flow."""

import uuid
from unittest.mock import MagicMock, patch

import pytest
import redis.asyncio as aioredis
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.service.models.passkey import PasskeyCredential
from com.qode.qrew.v1.service.models.user import KycStatus, User

# ── Shared test data ──────────────────────────────────────────────────────────

_EMAIL = "integration@example.com"
_PHONE = "+34612345678"
_PASSWORD = "Tr0ub4dor&3"
_FULL_NAME = "Integration Test"

_REGISTER_PAYLOAD: dict[str, object] = {
    "full_name": _FULL_NAME,
    "email": _EMAIL,
    "phone_number": _PHONE,
    "password": _PASSWORD,
    "terms_accepted": True,
    "captcha_token": "test-token",
}

_FAKE_ATTESTATION: dict[str, object] = {
    "id": "Y2hlY2tNZQ",
    "rawId": "Y2hlY2tNZQ",
    "response": {
        "clientDataJSON": "eyJ0eXBlIjoid2ViYXV0aG4uY3JlYXRlIn0",
        "attestationObject": "o2NmbXRkbm9uZWdhdHRTdG10oGhhdXRoRGF0YVik",
    },
    "type": "public-key",
}


def _fake_verified_registration() -> MagicMock:
    v = MagicMock()
    v.credential_id = b"fake-credential-id"
    v.credential_public_key = b"fake-public-key"
    v.sign_count = 0
    v.aaguid = uuid.UUID("00000000-0000-0000-0000-000000000000")
    return v


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _register(client: AsyncClient) -> None:
    r = await client.post("/v1/auth/register", json=_REGISTER_PAYLOAD)
    assert r.status_code == 201


async def _fetch_user(db: AsyncSession) -> User:
    result = await db.execute(select(User).where(User.email == _EMAIL))
    return result.scalar_one()


async def _verify_email(client: AsyncClient, token: str) -> None:
    r = await client.post("/v1/auth/verify-email", json={"token": token})
    assert r.status_code == 200


async def _login(client: AsyncClient) -> str:
    r = await client.post(
        "/v1/auth/login", json={"email": _EMAIL, "password": _PASSWORD}
    )
    assert r.status_code == 200
    return str(r.json()["access_token"])


# ── Happy path ────────────────────────────────────────────────────────────────


@pytest.mark.integration
async def test_full_post_login_verification_flow(  # noqa: PLR0915
    client: AsyncClient,
    db_session: AsyncSession,
    redis_test: aioredis.Redis,  # type: ignore[type-arg]
) -> None:
    """register → verify email → login → verify phone → KYC upload → passkey begin/complete"""  # noqa: E501

    # 1. Register
    response = await client.post("/v1/auth/register", json=_REGISTER_PAYLOAD)
    assert response.status_code == 201
    assert "Registration successful" in response.json()["message"]

    # 2. Read token + OTP
    user = await _fetch_user(db_session)
    assert not user.email_verified
    assert not user.phone_number_verified
    assert user.kyc_status == KycStatus.not_submitted

    email_token = user.email_verification_token
    phone_otp = user.phone_number_otp
    assert email_token is not None
    assert phone_otp is not None

    # 3. Verify email
    response = await client.post("/v1/auth/verify-email", json={"token": email_token})
    assert response.status_code == 200

    # 4. Login
    response = await client.post(
        "/v1/auth/login", json={"email": _EMAIL, "password": _PASSWORD}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["setup_required"] is True
    assert body["refresh_token"] is None
    access_token = body["access_token"]
    auth = {"Authorization": f"Bearer {access_token}"}

    # 5. Verify phone
    response = await client.post(
        "/v1/auth/verify-phone",
        json={"phone_number": _PHONE, "otp": phone_otp},
        headers=auth,
    )
    assert response.status_code == 200

    await db_session.refresh(user)
    assert user.phone_number_verified
    assert user.phone_number_otp is None

    # 6. KYC upload
    response = await client.post(
        "/v1/auth/kyc/upload",
        files={"document": ("id.jpg", b"fake-national-id-content", "image/jpeg")},
        headers=auth,
    )
    assert response.status_code == 200
    assert response.json()["kyc_status"] == "pending"

    await db_session.refresh(user)
    assert user.kyc_status == KycStatus.pending
    assert user.national_id_hash is not None

    # 7. Passkey register/begin
    response = await client.post("/v1/auth/passkey/register/begin", headers=auth)
    assert response.status_code == 200
    assert "challenge" in response.json()

    challenge_key = f"webauthn:challenge:{user.id}"
    assert await redis_test.get(challenge_key) is not None

    # 8. Passkey register/complete
    with patch(
        "com.qode.qrew.v1.service.services.passkey.webauthn.verify_registration_response",
        return_value=_fake_verified_registration(),
    ):
        response = await client.post(
            "/v1/auth/passkey/register/complete",
            json=_FAKE_ATTESTATION,
            headers=auth,
        )
    assert response.status_code == 200
    assert "registered" in response.json()["message"].lower()

    assert await redis_test.get(challenge_key) is None
    result = await db_session.execute(
        select(PasskeyCredential).where(PasskeyCredential.user_id == user.id)
    )
    cred = result.scalar_one_or_none()
    assert cred is not None
    assert cred.credential_id == b"fake-credential-id"
    assert cred.public_key == b"fake-public-key"
    assert cred.sign_count == 0

    # 9. Complete setup
    response = await client.post("/v1/auth/complete-setup", headers=auth)
    assert response.status_code == 200
    full = response.json()
    assert full["setup_required"] is False
    assert full["refresh_token"] is not None
    assert full["access_token"] != access_token


# ── Negative paths ────────────────────────────────────────────────────────────


@pytest.mark.integration
async def test_login_rejected_before_email_verification(
    client: AsyncClient,
) -> None:
    """Login must be blocked until the user verifies their email."""
    await _register(client)

    response = await client.post(
        "/v1/auth/login", json={"email": _EMAIL, "password": _PASSWORD}
    )
    assert response.status_code == 401
    assert "email" in response.json()["detail"]["message"].lower()


@pytest.mark.integration
async def test_phone_verify_rejected_for_wrong_number(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """A user must not be able to verify a phone number that isn't theirs."""
    await _register(client)
    user = await _fetch_user(db_session)
    assert user.email_verification_token is not None
    assert user.phone_number_otp is not None

    await _verify_email(client, user.email_verification_token)
    access_token = await _login(client)

    response = await client.post(
        "/v1/auth/verify-phone",
        json={"phone_number": "+34699999999", "otp": user.phone_number_otp},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 403


@pytest.mark.integration
async def test_kyc_upload_rejects_empty_file(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """KYC upload must reject an empty file with 400."""
    await _register(client)
    user = await _fetch_user(db_session)
    assert user.email_verification_token is not None

    await _verify_email(client, user.email_verification_token)
    access_token = await _login(client)

    response = await client.post(
        "/v1/auth/kyc/upload",
        files={"document": ("id.jpg", b"", "image/jpeg")},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 400

    await db_session.refresh(user)
    assert user.kyc_status == KycStatus.not_submitted


@pytest.mark.integration
async def test_passkey_complete_without_begin_is_rejected(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Completing passkey registration without a prior begin must return 400."""
    await _register(client)
    user = await _fetch_user(db_session)
    assert user.email_verification_token is not None

    await _verify_email(client, user.email_verification_token)
    access_token = await _login(client)

    # Skip begin — no challenge in Redis
    with patch(
        "com.qode.qrew.v1.service.services.passkey.webauthn.verify_registration_response",
        return_value=_fake_verified_registration(),
    ):
        response = await client.post(
            "/v1/auth/passkey/register/complete",
            json=_FAKE_ATTESTATION,
            headers={"Authorization": f"Bearer {access_token}"},
        )
    assert response.status_code == 400
    assert "expired" in response.json()["detail"]["message"].lower()


@pytest.mark.integration
async def test_passkey_authentication_flow(
    client: AsyncClient,
    db_session: AsyncSession,
    redis_test: aioredis.Redis,  # type: ignore[type-arg]
) -> None:
    """Full passkey authentication: register passkey then authenticate with it."""
    # 1. Complete the full onboarding flow first (reuse helpers)
    await _register(client)
    user = await _fetch_user(db_session)
    assert user.email_verification_token is not None

    await _verify_email(client, user.email_verification_token)
    setup_token = await _login(client)
    auth = {"Authorization": f"Bearer {setup_token}"}

    # Verify phone
    await client.post(
        "/v1/auth/verify-phone",
        json={"phone_number": _PHONE, "otp": user.phone_number_otp},
        headers=auth,
    )

    # KYC upload
    await client.post(
        "/v1/auth/kyc/upload",
        files={"document": ("id.jpg", b"fake-content", "image/jpeg")},
        headers=auth,
    )

    # Register passkey
    await client.post("/v1/auth/passkey/register/begin", headers=auth)
    with patch(
        "com.qode.qrew.v1.service.services.passkey.webauthn.verify_registration_response",
        return_value=_fake_verified_registration(),
    ):
        await client.post(
            "/v1/auth/passkey/register/complete",
            json=_FAKE_ATTESTATION,
            headers=auth,
        )

    # 2. Authenticate: begin — returns assertion options with a Redis challenge
    response = await client.post(
        "/v1/auth/passkey/authenticate/begin",
        json={"email": _EMAIL},
    )
    assert response.status_code == 200
    assert "challenge" in response.json()

    challenge_key = f"webauthn:auth:challenge:{user.id}"
    assert await redis_test.get(challenge_key) is not None

    # 3. Authenticate: complete — mock assertion verification
    fake_assertion: dict[str, object] = {
        "id": "ZmFrZS1jcmVkZW50aWFsLWlk",
        "rawId": "ZmFrZS1jcmVkZW50aWFsLWlk",
        "response": {
            "clientDataJSON": "eyJ0eXBlIjoid2ViYXV0aG4uZ2V0In0",
            "authenticatorData": "SZYN5YgOjGh0NBcPZHZgW4_krrmihjLHmVzzuoMdl2MFAAAABA",
            "signature": "MEYCIQDy0K2sGzrq7yGnxUBRyqvOBf5eRaKqMSuTvp6r1j8HqQ",
        },
        "type": "public-key",
    }

    def _fake_verified_auth() -> MagicMock:
        v = MagicMock()
        v.new_sign_count = 1
        return v

    with patch(
        "com.qode.qrew.v1.service.services.passkey.webauthn.verify_authentication_response",
        return_value=_fake_verified_auth(),
    ):
        response = await client.post(
            "/v1/auth/passkey/authenticate/complete",
            json=fake_assertion,
        )

    assert response.status_code == 200
    body = response.json()
    assert body["setup_required"] is False
    assert body["refresh_token"] is not None
    assert body["access_token"] is not None

    # Challenge must be consumed
    assert await redis_test.get(challenge_key) is None

    # sign_count and last_used_at must be updated in DB
    await db_session.refresh(user)
    result = await db_session.execute(
        select(PasskeyCredential).where(PasskeyCredential.user_id == user.id)
    )
    cred = result.scalar_one()
    assert cred.sign_count == 1
    assert cred.last_used_at is not None


@pytest.mark.integration
async def test_passkey_authenticate_begin_rejected_for_unknown_email(
    client: AsyncClient,
) -> None:
    """Begin must return 400 for an email that has no account."""
    response = await client.post(
        "/v1/auth/passkey/authenticate/begin",
        json={"email": "nobody@example.com"},
    )
    assert response.status_code == 400


@pytest.mark.integration
async def test_passkey_authenticate_complete_without_begin_is_rejected(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Completing passkey authentication without a prior begin must return 400."""
    await _register(client)
    user = await _fetch_user(db_session)
    assert user.email_verification_token is not None

    await _verify_email(client, user.email_verification_token)
    setup_token = await _login(client)
    auth = {"Authorization": f"Bearer {setup_token}"}

    # Register a passkey so the credential exists in the DB
    await client.post("/v1/auth/passkey/register/begin", headers=auth)
    with patch(
        "com.qode.qrew.v1.service.services.passkey.webauthn.verify_registration_response",
        return_value=_fake_verified_registration(),
    ):
        await client.post(
            "/v1/auth/passkey/register/complete",
            json=_FAKE_ATTESTATION,
            headers=auth,
        )

    # Skip authenticate/begin — no auth challenge in Redis
    fake_assertion: dict[str, object] = {
        "id": "ZmFrZS1jcmVkZW50aWFsLWlk",
        "rawId": "ZmFrZS1jcmVkZW50aWFsLWlk",
        "response": {
            "clientDataJSON": "eyJ0eXBlIjoid2ViYXV0aG4uZ2V0In0",
            "authenticatorData": "SZYN5YgOjGh0NBcPZHZgW4_krrmihjLHmVzzuoMdl2MFAAAABA",
            "signature": "MEYCIQDy0K2sGzrq7yGnxUBRyqvOBf5eRaKqMSuTvp6r1j8HqQ",
        },
        "type": "public-key",
    }
    with patch(
        "com.qode.qrew.v1.service.services.passkey.webauthn.verify_authentication_response",
        return_value=MagicMock(new_sign_count=1),
    ):
        response = await client.post(
            "/v1/auth/passkey/authenticate/complete",
            json=fake_assertion,
        )
    assert response.status_code == 400
    assert "expired" in response.json()["detail"]["message"].lower()
