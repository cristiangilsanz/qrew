import httpx
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]


class TestGetMe:
    async def test_returns_profile_for_authenticated_user(
        self, client: httpx.AsyncClient, auth_headers: dict, registered_user: dict
    ) -> None:
        resp = await client.get("/v1/auth/profile/me", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["email"] == registered_user["email"]
        assert body["email_verified"] is True

    async def test_unauthenticated_returns_401(self, client: httpx.AsyncClient) -> None:
        resp = await client.get("/v1/auth/profile/me")
        assert resp.status_code == 401


class TestOnboardingStatus:
    async def test_returns_status_for_authenticated_user(
        self, client: httpx.AsyncClient, auth_headers: dict
    ) -> None:
        resp = await client.get("/v1/auth/profile/onboarding-status", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "email_verified" in body
        assert "phone_verified" in body
        assert "kyc_submitted" in body
        assert "passkey_registered" in body
        assert "is_complete" in body

    async def test_email_verified_is_true_after_verify(
        self, client: httpx.AsyncClient, auth_headers: dict
    ) -> None:
        resp = await client.get("/v1/auth/profile/onboarding-status", headers=auth_headers)
        assert resp.json()["email_verified"] is True


class TestAuditLog:
    async def test_returns_paginated_audit_events(
        self, client: httpx.AsyncClient, auth_headers: dict
    ) -> None:
        resp = await client.get("/v1/auth/profile/audit", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
