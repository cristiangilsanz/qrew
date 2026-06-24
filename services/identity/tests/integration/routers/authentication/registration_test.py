import uuid

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]

_DEFAULT_PASSWORD = "StrongP@ss1!"


def _payload(**overrides) -> dict:
    base = {
        "full_name": "Test User",
        "email": f"reg-{uuid.uuid4().hex[:8]}@example.com",
        "phone_number": f"+316{str(int(uuid.uuid4().int % 9_000_000) + 1_000_000)}",
        "password": _DEFAULT_PASSWORD,
        "terms_accepted": True,
        "captcha_token": "test-token",
    }
    return {**base, **overrides}


class TestRegister:
    async def test_creates_user_and_returns_id(self, client: httpx.AsyncClient) -> None:
        resp = await client.post("/v1/auth/registration/", json=_payload())
        assert resp.status_code == 201
        body = resp.json()
        assert "id" in body
        assert uuid.UUID(body["id"])

    async def test_duplicate_email_returns_409(self, client: httpx.AsyncClient) -> None:
        payload = _payload()
        await client.post("/v1/auth/registration/", json=payload)
        resp2 = await client.post(
            "/v1/auth/registration/",
            json={
                **payload,
                "phone_number": f"+316{str(int(uuid.uuid4().int % 9_000_000) + 1_000_000)}",
            },
        )
        assert resp2.status_code == 409

    async def test_weak_password_returns_422(self, client: httpx.AsyncClient) -> None:
        resp = await client.post("/v1/auth/registration/", json=_payload(password="weak"))
        assert resp.status_code == 422

    async def test_missing_terms_returns_422(self, client: httpx.AsyncClient) -> None:
        resp = await client.post("/v1/auth/registration/", json=_payload(terms_accepted=False))
        assert resp.status_code == 422

    async def test_invalid_email_returns_422(self, client: httpx.AsyncClient) -> None:
        resp = await client.post("/v1/auth/registration/", json=_payload(email="not-an-email"))
        assert resp.status_code == 422


class TestVerifyEmail:
    async def test_valid_token_verifies(
        self, client: httpx.AsyncClient, db_session: AsyncSession
    ) -> None:
        import uuid as _uuid
        from sqlalchemy import select
        from com.qode.qrew.v1.identity.models.user import User

        payload = _payload()
        resp = await client.post("/v1/auth/registration/", json=payload)
        user_id = _uuid.UUID(resp.json()["id"])

        result = await db_session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one()
        token = user.email_verification_token

        verify_resp = await client.post("/v1/auth/registration/verify-email", json={"token": token})
        assert verify_resp.status_code == 200

    async def test_invalid_token_returns_400(self, client: httpx.AsyncClient) -> None:
        resp = await client.post("/v1/auth/registration/verify-email", json={"token": "bad-token"})
        assert resp.status_code == 400


class TestResendEmailVerification:
    async def test_resend_returns_200(self, client: httpx.AsyncClient) -> None:
        payload = _payload()
        await client.post("/v1/auth/registration/", json=payload)
        resp = await client.post(
            "/v1/auth/registration/resend-email-verification",
            json={"email": payload["email"]},
        )
        assert resp.status_code == 200

    async def test_unknown_email_still_returns_200(self, client: httpx.AsyncClient) -> None:
        resp = await client.post(
            "/v1/auth/registration/resend-email-verification",
            json={"email": "nobody@example.com"},
        )
        assert resp.status_code == 200
