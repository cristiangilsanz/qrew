import httpx
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]


class TestLogin:
    async def test_valid_credentials_return_tokens(
        self, client: httpx.AsyncClient, registered_user: dict
    ) -> None:
        resp = await client.post(
            "/v1/auth/login",
            json={"email": registered_user["email"], "password": registered_user["password"]},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["access_token"]
        assert body["token_type"] == "bearer"

    async def test_wrong_password_returns_401(
        self, client: httpx.AsyncClient, registered_user: dict
    ) -> None:
        resp = await client.post(
            "/v1/auth/login",
            json={"email": registered_user["email"], "password": "WrongPass1!"},
        )
        assert resp.status_code == 401

    async def test_unknown_email_returns_401(self, client: httpx.AsyncClient) -> None:
        resp = await client.post(
            "/v1/auth/login",
            json={"email": "nobody@example.com", "password": "SomePass1!"},
        )
        assert resp.status_code == 401

    async def test_unverified_email_returns_setup_required(self, client: httpx.AsyncClient) -> None:
        import uuid

        email = f"unverified-{uuid.uuid4().hex[:8]}@example.com"
        phone = f"+316{str(int(uuid.uuid4().int % 9_000_000) + 1_000_000)}"
        await client.post(
            "/v1/auth/registration/",
            json={
                "full_name": "Unverified User",
                "email": email,
                "phone_number": phone,
                "password": "StrongP@ss1!",
                "terms_accepted": True,
                "captcha_token": "test-token",
            },
        )
        resp = await client.post(
            "/v1/auth/login",
            json={"email": email, "password": "StrongP@ss1!"},
        )
        assert resp.status_code == 200
        assert resp.json()["setup_required"] is True


class TestRefresh:
    async def test_valid_refresh_token_rotates(
        self, client: httpx.AsyncClient, registered_user: dict
    ) -> None:
        login_resp = await client.post(
            "/v1/auth/login",
            json={"email": registered_user["email"], "password": registered_user["password"]},
        )
        refresh_token = login_resp.json()["refresh_token"]
        assert refresh_token

        resp = await client.post("/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert resp.status_code == 200
        body = resp.json()
        assert body["access_token"]
        assert body["refresh_token"]

    async def test_invalid_refresh_token_returns_401(self, client: httpx.AsyncClient) -> None:
        resp = await client.post("/v1/auth/refresh", json={"refresh_token": "bad.token.here"})
        assert resp.status_code == 401


class TestLogout:
    async def test_logout_invalidates_refresh_token(
        self, client: httpx.AsyncClient, registered_user: dict
    ) -> None:
        login_resp = await client.post(
            "/v1/auth/login",
            json={"email": registered_user["email"], "password": registered_user["password"]},
        )
        refresh_token = login_resp.json()["refresh_token"]

        logout_resp = await client.post("/v1/auth/logout", json={"refresh_token": refresh_token})
        assert logout_resp.status_code == 200

        # Second refresh should now fail.
        refresh_resp = await client.post("/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert refresh_resp.status_code == 401
