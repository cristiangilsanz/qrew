import httpx
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]


class TestListUsers:
    async def test_returns_paginated_users(
        self, client: httpx.AsyncClient, admin_headers: dict, registered_user: dict
    ) -> None:
        resp = await client.get("/v1/admin/users", headers=admin_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert isinstance(body["items"], list)

    async def test_search_by_email_fragment(
        self,
        client: httpx.AsyncClient,
        admin_headers: dict,
        registered_user: dict,
    ) -> None:
        fragment = registered_user["email"][:6]
        resp = await client.get(
            "/v1/admin/users", params={"search": fragment}, headers=admin_headers
        )
        assert resp.status_code == 200

    async def test_non_admin_returns_403(
        self, client: httpx.AsyncClient, auth_headers: dict
    ) -> None:
        resp = await client.get("/v1/admin/users", headers=auth_headers)
        assert resp.status_code == 403

    async def test_unauthenticated_returns_401(self, client: httpx.AsyncClient) -> None:
        resp = await client.get("/v1/admin/users")
        assert resp.status_code == 401
