import httpx
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]


class TestGetFingerprint:
    async def test_unknown_hash_returns_empty_list(
        self, client: httpx.AsyncClient, admin_headers: dict
    ) -> None:
        resp = await client.get("/v1/admin/fingerprints/deadbeef1234", headers=admin_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["account_count"] == 0
        assert body["user_ids"] == []

    async def test_known_hash_returned_after_fingerprint_report(
        self, client: httpx.AsyncClient, auth_headers: dict, admin_headers: dict
    ) -> None:
        fp_hash = "testfingerprinthash999"
        await client.post(
            "/v1/auth/devices/fingerprint",
            headers=auth_headers,
            json={
                "fingerprint_hash": fp_hash,
                "user_agent": "pytest/1.0",
                "ip_address": "127.0.0.1",
            },
        )
        resp = await client.get(f"/v1/admin/fingerprints/{fp_hash}", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["account_count"] >= 1

    async def test_non_admin_returns_403(
        self, client: httpx.AsyncClient, auth_headers: dict
    ) -> None:
        resp = await client.get("/v1/admin/fingerprints/abc", headers=auth_headers)
        assert resp.status_code == 403

    async def test_unauthenticated_returns_401(self, client: httpx.AsyncClient) -> None:
        resp = await client.get("/v1/admin/fingerprints/abc")
        assert resp.status_code == 401
