"""Integration tests for the full auth verification flow."""

import uuid
from unittest.mock import MagicMock, patch

import pytest
import redis.asyncio as aioredis
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.service.core.security import create_refresh_token
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


async def _make_setup_complete(db: AsyncSession, user: User) -> None:
    """Force a user into a fully-setup state via direct DB writes."""
    user.phone_number_verified = True
    user.kyc_status = KycStatus.pending
    db.add(
        PasskeyCredential(
            id=uuid.uuid4(),
            user_id=user.id,
            credential_id=b"cred",
            public_key=b"pk",
            sign_count=0,
            aaguid="00000000-0000-0000-0000-000000000000",
        )
    )
    await db.commit()
    await db.refresh(user)


# ── Happy path ────────────────────────────────────────────────────────────────


@pytest.mark.integration
async def test_full_post_login_verification_flow(  # noqa: PLR0915
    client: AsyncClient,
    db_session: AsyncSession,
    redis_test: aioredis.Redis,  # type: ignore[type-arg]
) -> None:
    """register → verify email → login → verify phone → KYC upload → passkey begin/complete"""  # noqa: E501

    # Given
    response = await client.post("/v1/auth/register", json=_REGISTER_PAYLOAD)
    assert response.status_code == 201
    assert "Registration successful" in response.json()["message"]

    user = await _fetch_user(db_session)
    assert not user.email_verified
    assert not user.phone_number_verified
    assert user.kyc_status == KycStatus.not_submitted

    email_token = user.email_verification_token
    phone_otp = user.phone_number_otp
    assert email_token is not None
    assert phone_otp is not None

    response = await client.post("/v1/auth/verify-email", json={"token": email_token})
    assert response.status_code == 200

    # When
    response = await client.post(
        "/v1/auth/login", json={"email": _EMAIL, "password": _PASSWORD}
    )

    # Then
    assert response.status_code == 200
    body = response.json()
    assert body["setup_required"] is True
    assert body["refresh_token"] is None
    access_token = body["access_token"]
    auth = {"Authorization": f"Bearer {access_token}"}

    response = await client.post(
        "/v1/auth/verify-phone",
        json={"phone_number": _PHONE, "otp": phone_otp},
        headers=auth,
    )
    assert response.status_code == 200

    await db_session.refresh(user)
    assert user.phone_number_verified
    assert user.phone_number_otp is None

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

    response = await client.post("/v1/auth/passkey/register/begin", headers=auth)
    assert response.status_code == 200
    assert "challenge" in response.json()

    challenge_key = f"webauthn:challenge:{user.id}"
    assert await redis_test.get(challenge_key) is not None

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
    # Given
    await _register(client)

    # When
    response = await client.post(
        "/v1/auth/login", json={"email": _EMAIL, "password": _PASSWORD}
    )

    # Then
    assert response.status_code == 401
    assert "email" in response.json()["detail"]["message"].lower()


@pytest.mark.integration
async def test_phone_verify_rejected_for_wrong_number(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """A user must not be able to verify a phone number that isn't theirs."""
    # Given
    await _register(client)
    user = await _fetch_user(db_session)
    assert user.email_verification_token is not None
    assert user.phone_number_otp is not None

    await _verify_email(client, user.email_verification_token)
    access_token = await _login(client)

    # When
    response = await client.post(
        "/v1/auth/verify-phone",
        json={"phone_number": "+34699999999", "otp": user.phone_number_otp},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    # Then
    assert response.status_code == 403


@pytest.mark.integration
async def test_kyc_upload_rejects_empty_file(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """KYC upload must reject an empty file with 400."""
    # Given
    await _register(client)
    user = await _fetch_user(db_session)
    assert user.email_verification_token is not None

    await _verify_email(client, user.email_verification_token)
    access_token = await _login(client)

    # When
    response = await client.post(
        "/v1/auth/kyc/upload",
        files={"document": ("id.jpg", b"", "image/jpeg")},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    # Then
    assert response.status_code == 400

    await db_session.refresh(user)
    assert user.kyc_status == KycStatus.not_submitted


@pytest.mark.integration
async def test_passkey_complete_without_begin_is_rejected(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Completing passkey registration without a prior begin must return 400."""
    # Given
    await _register(client)
    user = await _fetch_user(db_session)
    assert user.email_verification_token is not None

    await _verify_email(client, user.email_verification_token)
    access_token = await _login(client)

    # When
    with patch(
        "com.qode.qrew.v1.service.services.passkey.webauthn.verify_registration_response",
        return_value=_fake_verified_registration(),
    ):
        response = await client.post(
            "/v1/auth/passkey/register/complete",
            json=_FAKE_ATTESTATION,
            headers={"Authorization": f"Bearer {access_token}"},
        )

    # Then
    assert response.status_code == 400
    assert "expired" in response.json()["detail"]["message"].lower()


@pytest.mark.integration
async def test_passkey_authentication_flow(
    client: AsyncClient,
    db_session: AsyncSession,
    redis_test: aioredis.Redis,  # type: ignore[type-arg]
) -> None:
    """Full passkey authentication: register passkey then authenticate with it."""
    # Given
    await _register(client)
    user = await _fetch_user(db_session)
    assert user.email_verification_token is not None

    await _verify_email(client, user.email_verification_token)
    setup_token = await _login(client)
    auth = {"Authorization": f"Bearer {setup_token}"}

    await client.post(
        "/v1/auth/verify-phone",
        json={"phone_number": _PHONE, "otp": user.phone_number_otp},
        headers=auth,
    )

    await client.post(
        "/v1/auth/kyc/upload",
        files={"document": ("id.jpg", b"fake-content", "image/jpeg")},
        headers=auth,
    )

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

    # When
    response = await client.post(
        "/v1/auth/passkey/authenticate/begin",
        json={"email": _EMAIL},
    )

    # Then
    assert response.status_code == 200
    assert "challenge" in response.json()

    challenge_key = f"webauthn:auth:challenge:{user.id}"
    assert await redis_test.get(challenge_key) is not None

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

    assert await redis_test.get(challenge_key) is None

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
    # When
    response = await client.post(
        "/v1/auth/passkey/authenticate/begin",
        json={"email": "nobody@example.com"},
    )

    # Then
    assert response.status_code == 400


@pytest.mark.integration
async def test_passkey_authenticate_complete_without_begin_is_rejected(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Completing passkey authentication without a prior begin must return 400."""
    # Given
    await _register(client)
    user = await _fetch_user(db_session)
    assert user.email_verification_token is not None

    await _verify_email(client, user.email_verification_token)
    setup_token = await _login(client)
    auth = {"Authorization": f"Bearer {setup_token}"}

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

    # When
    with patch(
        "com.qode.qrew.v1.service.services.passkey.webauthn.verify_authentication_response",
        return_value=MagicMock(new_sign_count=1),
    ):
        response = await client.post(
            "/v1/auth/passkey/authenticate/complete",
            json=fake_assertion,
        )

    # Then
    assert response.status_code == 400
    assert "expired" in response.json()["detail"]["message"].lower()


# ── Logout ────────────────────────────────────────────────────────────────────


@pytest.mark.integration
async def test_logout_invalidates_refresh_token(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Logout → subsequent refresh is rejected with 401."""
    # Given
    await _register(client)
    user = await _fetch_user(db_session)
    await _verify_email(client, str(user.email_verification_token))

    refresh_token = create_refresh_token(str(user.id))

    # When
    r = await client.post("/v1/auth/logout", json={"refresh_token": refresh_token})

    # Then
    assert r.status_code == 200
    assert "logged out" in r.json()["message"].lower()

    r = await client.post("/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert r.status_code == 401
    assert "revoked" in r.json()["detail"]["message"].lower()


@pytest.mark.integration
async def test_logout_with_invalid_token_returns_401(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    # When
    r = await client.post(
        "/v1/auth/logout", json={"refresh_token": "not.a.valid.token"}
    )

    # Then
    assert r.status_code == 401


# ── Refresh token rotation ────────────────────────────────────────────────────


@pytest.mark.integration
async def test_refresh_rotates_token(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Each /refresh call returns a new refresh token; old one is invalidated."""
    # Given
    await _register(client)
    user = await _fetch_user(db_session)
    await _verify_email(client, str(user.email_verification_token))

    original = create_refresh_token(str(user.id))

    # When
    r = await client.post("/v1/auth/refresh", json={"refresh_token": original})

    # Then
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert "refresh_token" in body
    new_token = body["refresh_token"]
    assert new_token != original

    r2 = await client.post("/v1/auth/refresh", json={"refresh_token": original})
    assert r2.status_code == 401
    assert "revoked" in r2.json()["detail"]["message"].lower()


@pytest.mark.integration
async def test_refresh_reuse_after_rotation_triggers_revocation(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Replaying a rotated refresh token invalidates all tokens for the user."""
    # Given
    await _register(client)
    user = await _fetch_user(db_session)
    await _verify_email(client, str(user.email_verification_token))

    original = create_refresh_token(str(user.id))

    r = await client.post("/v1/auth/refresh", json={"refresh_token": original})
    assert r.status_code == 200
    new_token = r.json()["refresh_token"]

    # When
    r2 = await client.post("/v1/auth/refresh", json={"refresh_token": original})

    # Then
    assert r2.status_code == 401

    r3 = await client.post("/v1/auth/refresh", json={"refresh_token": new_token})
    assert r3.status_code == 401


# ── Session management ────────────────────────────────────────────────────────


@pytest.mark.integration
async def test_login_creates_session(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """A full login persists a session row visible via GET /sessions."""
    # Given
    await _register(client)
    user = await _fetch_user(db_session)
    await _verify_email(client, str(user.email_verification_token))
    await _make_setup_complete(db_session, user)
    access_token = await _login(client)

    # When
    r = await client.get(
        "/v1/auth/sessions",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    # Then
    assert r.status_code == 200
    sessions = r.json()["sessions"]
    assert len(sessions) == 1
    assert sessions[0]["jti"] is not None


@pytest.mark.integration
async def test_revoke_session_invalidates_refresh_token(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Revoking a session via DELETE /sessions/{jti} blacklists its refresh token."""
    # Given
    await _register(client)
    user = await _fetch_user(db_session)
    await _verify_email(client, str(user.email_verification_token))
    await _make_setup_complete(db_session, user)
    access_token = await _login(client)
    auth = {"Authorization": f"Bearer {access_token}"}

    r = await client.get("/v1/auth/sessions", headers=auth)
    jti = r.json()["sessions"][0]["jti"]

    # When
    r = await client.delete(f"/v1/auth/sessions/{jti}", headers=auth)

    # Then
    assert r.status_code == 204

    r = await client.get("/v1/auth/sessions", headers=auth)
    assert r.json()["sessions"] == []


@pytest.mark.integration
async def test_revoke_all_sessions(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """POST /sessions/revoke-all removes all sessions for the user."""
    # Given
    await _register(client)
    user = await _fetch_user(db_session)
    await _verify_email(client, str(user.email_verification_token))
    await _make_setup_complete(db_session, user)
    access_token = await _login(client)
    auth = {"Authorization": f"Bearer {access_token}"}

    # When
    r = await client.post("/v1/auth/sessions/revoke-all", headers=auth)

    # Then
    assert r.status_code == 200
    assert "revoked" in r.json()["message"].lower()

    r = await client.get("/v1/auth/sessions", headers=auth)
    assert r.json()["sessions"] == []


@pytest.mark.integration
async def test_revoke_nonexistent_session_returns_404(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    # Given
    await _register(client)
    user = await _fetch_user(db_session)
    await _verify_email(client, str(user.email_verification_token))
    await _make_setup_complete(db_session, user)
    access_token = await _login(client)
    auth = {"Authorization": f"Bearer {access_token}"}

    # When
    r = await client.delete("/v1/auth/sessions/no-such-jti", headers=auth)

    # Then
    assert r.status_code == 404
