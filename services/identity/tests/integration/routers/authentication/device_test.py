import httpx
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]


class TestListDevices:
    async def test_returns_empty_list_initially(
        self, client: httpx.AsyncClient, auth_headers: dict
    ) -> None:
        resp = await client.get("/v1/auth/devices", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"] == []

    async def test_unauthenticated_returns_401(self, client: httpx.AsyncClient) -> None:
        resp = await client.get("/v1/auth/devices")
        assert resp.status_code == 401


class TestReportFingerprint:
    async def test_valid_fingerprint_returns_200(
        self, client: httpx.AsyncClient, auth_headers: dict
    ) -> None:
        resp = await client.post(
            "/v1/auth/devices/fingerprint",
            headers=auth_headers,
            json={
                "fingerprint_hash": "abc123def456",
                "user_agent": "pytest/1.0",
                "ip_address": "127.0.0.1",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "flagged" in body


class TestDeviceBind:
    async def test_bind_begin_returns_challenge(
        self, client: httpx.AsyncClient, auth_headers: dict
    ) -> None:
        resp = await client.post("/v1/auth/devices/bind/begin", headers=auth_headers)
        assert resp.status_code == 200
        assert "challenge" in resp.json()

    async def test_bind_complete_with_bad_signature_returns_400(
        self, client: httpx.AsyncClient, auth_headers: dict
    ) -> None:
        resp = await client.post(
            "/v1/auth/devices/bind/complete",
            headers=auth_headers,
            json={
                "name": "My Device",
                "public_key": "not-a-real-public-key",
                "signature": "not-a-real-signature",
            },
        )
        assert resp.status_code == 400


class TestRevokeDevice:
    async def test_revoke_nonexistent_device_returns_400(
        self, client: httpx.AsyncClient, auth_headers: dict
    ) -> None:
        import uuid

        resp = await client.post(f"/v1/auth/devices/{uuid.uuid4()}/revoke", headers=auth_headers)
        assert resp.status_code == 400
