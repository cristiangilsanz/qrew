import httpx
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]

_DEFAULT_PASSWORD = "StrongP@ss1!"
_NEW_PASSWORD = "NewStrongP@ss2!"


class TestChangePassword:
    async def test_valid_change_returns_200(
        self, client: httpx.AsyncClient, auth_headers: dict, registered_user: dict
    ) -> None:
        resp = await client.post(
            "/v1/auth/account/change-password",
            headers=auth_headers,
            json={
                "current_password": registered_user["password"],
                "new_password": _NEW_PASSWORD,
            },
        )
        assert resp.status_code == 200

    async def test_wrong_current_password_returns_400(
        self, client: httpx.AsyncClient, auth_headers: dict
    ) -> None:
        resp = await client.post(
            "/v1/auth/account/change-password",
            headers=auth_headers,
            json={"current_password": "WrongPass1!", "new_password": _NEW_PASSWORD},
        )
        assert resp.status_code == 400

    async def test_unauthenticated_returns_401(self, client: httpx.AsyncClient) -> None:
        resp = await client.post(
            "/v1/auth/account/change-password",
            json={"current_password": _DEFAULT_PASSWORD, "new_password": _NEW_PASSWORD},
        )
        assert resp.status_code == 401


class TestDeleteAccount:
    async def test_valid_deletion_returns_200(
        self, client: httpx.AsyncClient, registered_user: dict
    ) -> None:
        # Use fresh login so deleting this account doesn't affect other tests.
        login_resp = await client.post(
            "/v1/auth/login",
            json={
                "email": registered_user["email"],
                "password": registered_user["password"],
            },
        )
        headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

        resp = await client.post(
            "/v1/auth/account/delete",
            headers=headers,
            json={"current_password": registered_user["password"]},
        )
        assert resp.status_code == 200

    async def test_wrong_password_returns_400(
        self, client: httpx.AsyncClient, auth_headers: dict
    ) -> None:
        resp = await client.post(
            "/v1/auth/account/delete",
            headers=auth_headers,
            json={"current_password": "WrongPass1!"},
        )
        assert resp.status_code == 400


class TestChangeEmail:
    async def test_change_email_request_returns_200(
        self, client: httpx.AsyncClient, auth_headers: dict, registered_user: dict
    ) -> None:
        import uuid

        new_email = f"new-{uuid.uuid4().hex[:8]}@example.com"
        resp = await client.post(
            "/v1/auth/account/change-email",
            headers=auth_headers,
            json={
                "new_email": new_email,
                "current_password": registered_user["password"],
            },
        )
        assert resp.status_code == 200

    async def test_invalid_token_confirm_returns_400(self, client: httpx.AsyncClient) -> None:
        resp = await client.post(
            "/v1/auth/account/confirm-email-change",
            json={"token": "bad-token"},
        )
        assert resp.status_code == 400


class TestChangePhone:
    async def test_change_phone_request_returns_200(
        self, client: httpx.AsyncClient, auth_headers: dict, registered_user: dict
    ) -> None:
        import uuid

        new_phone = f"+317{str(int(uuid.uuid4().int % 9_000_000) + 1_000_000)}"
        resp = await client.post(
            "/v1/auth/account/change-phone",
            headers=auth_headers,
            json={
                "new_phone_number": new_phone,
                "current_password": registered_user["password"],
            },
        )
        assert resp.status_code == 200
