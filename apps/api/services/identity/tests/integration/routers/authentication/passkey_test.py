import httpx
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]


class TestPasskeyRegisterBegin:
    async def test_returns_options_json(
        self, client: httpx.AsyncClient, auth_headers: dict
    ) -> None:
        resp = await client.post("/v1/auth/passkeys/register/begin", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("application/json")

    async def test_unauthenticated_returns_401(self, client: httpx.AsyncClient) -> None:
        resp = await client.post("/v1/auth/passkeys/register/begin")
        assert resp.status_code == 401


class TestPasskeyRegisterComplete:
    async def test_invalid_response_returns_400(
        self, client: httpx.AsyncClient, auth_headers: dict
    ) -> None:
        resp = await client.post(
            "/v1/auth/passkeys/register/complete",
            headers=auth_headers,
            json={"credential": "not-valid-webauthn-data"},
        )
        assert resp.status_code in (400, 422)


class TestPasskeyList:
    async def test_returns_empty_list_initially(
        self, client: httpx.AsyncClient, auth_headers: dict
    ) -> None:
        resp = await client.get("/v1/auth/passkeys", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["items"] == []


class TestPasskeyAuthBegin:
    async def test_no_email_returns_200_or_400(self, client: httpx.AsyncClient) -> None:
        resp = await client.post("/v1/auth/passkeys/authenticate/begin", json={})
        assert resp.status_code in (200, 400, 422)

    async def test_unknown_email_returns_200_or_404(self, client: httpx.AsyncClient) -> None:
        resp = await client.post(
            "/v1/auth/passkeys/authenticate/begin",
            json={"email": "nobody@example.com"},
        )
        assert resp.status_code in (200, 404)
