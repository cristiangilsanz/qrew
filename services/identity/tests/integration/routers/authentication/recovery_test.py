import io

import httpx
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]


class TestRecoveryBegin:
    async def test_unknown_email_returns_200_with_generic_message(
        self, client: httpx.AsyncClient
    ) -> None:
        # Recovery must not leak whether an account exists.
        fake_image = io.BytesIO(b"fake-image-data")
        resp = await client.post(
            "/v1/auth/recovery/begin",
            data={"email": "nobody@example.com"},
            files={"document": ("id.jpg", fake_image, "image/jpeg")},
        )
        assert resp.status_code == 200
        assert "message" in resp.json()

    async def test_missing_document_returns_422(self, client: httpx.AsyncClient) -> None:
        resp = await client.post(
            "/v1/auth/recovery/begin",
            data={"email": "test@example.com"},
        )
        assert resp.status_code == 422

    async def test_missing_email_returns_422(self, client: httpx.AsyncClient) -> None:
        fake_image = io.BytesIO(b"fake-image-data")
        resp = await client.post(
            "/v1/auth/recovery/begin",
            files={"document": ("id.jpg", fake_image, "image/jpeg")},
        )
        assert resp.status_code == 422
