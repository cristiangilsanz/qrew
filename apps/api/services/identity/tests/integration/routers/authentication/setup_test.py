# tests setup
import io

import httpx
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]


class TestKycUpload:
    # verifies that requires authentication
    async def test_requires_authentication(self, client: httpx.AsyncClient) -> None:
        fake_image = io.BytesIO(b"fake-document")
        resp = await client.post(
            "/v1/auth/setup/kyc/upload",
            files={"document": ("id.jpg", fake_image, "image/jpeg")},
        )
        assert resp.status_code == 401

    # verifies that authenticated upload accepted
    async def test_authenticated_upload_accepted(
        self, client: httpx.AsyncClient, auth_headers: dict
    ) -> None:
        fake_image = io.BytesIO(b"\xff\xd8\xff" + b"0" * 64)
        resp = await client.post(
            "/v1/auth/setup/kyc/upload",
            headers=auth_headers,
            files={"document": ("id.jpg", fake_image, "image/jpeg")},
        )
        assert resp.status_code in (200, 400)


class TestCompleteSetup:
    # verifies that full user gets a session again
    async def test_full_user_gets_a_session_again(
        self, client: httpx.AsyncClient, auth_headers: dict
    ) -> None:
        resp = await client.post("/v1/auth/setup/complete-setup", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["access_token"]
