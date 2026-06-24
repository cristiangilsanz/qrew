import httpx
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]


class TestListSessions:
    async def test_returns_current_session(
        self, client: httpx.AsyncClient, auth_headers: dict
    ) -> None:
        resp = await client.get("/v1/auth/sessions", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert len(body["items"]) >= 1

    async def test_unauthenticated_returns_401(self, client: httpx.AsyncClient) -> None:
        resp = await client.get("/v1/auth/sessions")
        assert resp.status_code == 401


class TestRevokeSession:
    async def test_revoke_specific_session(
        self, client: httpx.AsyncClient, registered_user: dict
    ) -> None:
        login_resp = await client.post(
            "/v1/auth/login",
            json={"email": registered_user["email"], "password": registered_user["password"]},
        )
        access_token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        sessions_resp = await client.get("/v1/auth/sessions", headers=headers)
        sessions = sessions_resp.json()["items"]
        jti = sessions[0]["jti"]

        resp = await client.delete(f"/v1/auth/sessions/{jti}", headers=headers)
        assert resp.status_code == 204

    async def test_revoke_nonexistent_jti_returns_404(
        self, client: httpx.AsyncClient, auth_headers: dict
    ) -> None:
        resp = await client.delete("/v1/auth/sessions/nonexistent-jti", headers=auth_headers)
        assert resp.status_code == 404


class TestRevokeAllSessions:
    async def test_revoke_all_returns_200(
        self, client: httpx.AsyncClient, auth_headers: dict
    ) -> None:
        resp = await client.post("/v1/auth/sessions/revoke-all", headers=auth_headers)
        assert resp.status_code == 200
        assert "message" in resp.json()
