import io

import httpx
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]


class TestKycUpload:
    async def test_requires_authentication(self, client: httpx.AsyncClient) -> None:
        fake_image = io.BytesIO(b"fake-document")
        resp = await client.post(
            "/v1/auth/setup/kyc/upload",
            files={"document": ("id.jpg", fake_image, "image/jpeg")},
        )
        assert resp.status_code == 401

    async def test_authenticated_upload_accepted(
        self, client: httpx.AsyncClient, auth_headers: dict
    ) -> None:
        # OCR will fail on a fake image but the endpoint should still return 400 not 500.
        fake_image = io.BytesIO(b"not-a-real-image")
        resp = await client.post(
            "/v1/auth/setup/kyc/upload",
            headers=auth_headers,
            files={"document": ("id.jpg", fake_image, "image/jpeg")},
        )
        # 200 if OCR succeeded (unlikely with fake data) or 400 if it couldn't parse.
        assert resp.status_code in (200, 400)


class TestCompleteSetup:
    async def test_full_user_cannot_use_complete_setup(
        self, client: httpx.AsyncClient, auth_headers: dict
    ) -> None:
        # auth_headers belong to a fully-verified user (not in setup flow).
        # complete-setup is only valid with a setup token; a regular access token is rejected.
        resp = await client.post("/v1/auth/setup/complete-setup", headers=auth_headers)
        # Either 400 (wrong token type) or 401 (token validation rejects full token here).
        assert resp.status_code in (400, 401)
