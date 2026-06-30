import httpx
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]


class TestListDlq:
    async def test_returns_empty_list_on_fresh_db(
        self, client: httpx.AsyncClient, admin_headers: dict
    ) -> None:
        resp = await client.get("/v1/admin/outbox/dlq", headers=admin_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert isinstance(body["items"], list)

    async def test_non_admin_returns_403(
        self, client: httpx.AsyncClient, auth_headers: dict
    ) -> None:
        resp = await client.get("/v1/admin/outbox/dlq", headers=auth_headers)
        assert resp.status_code == 403

    async def test_unauthenticated_returns_401(self, client: httpx.AsyncClient) -> None:
        resp = await client.get("/v1/admin/outbox/dlq")
        assert resp.status_code == 401
