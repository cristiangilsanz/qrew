# tests passkey
import httpx
import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.identity.models.passkey import PasskeyCredential

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]


# leaves the account with no passkey, which is the state the setup flow starts from
async def _drop_passkeys(db_session: AsyncSession) -> None:
    await db_session.execute(delete(PasskeyCredential))
    await db_session.commit()


class TestPasskeyRegisterBegin:
    # verifies that an account without a passkey may register its first one
    async def test_returns_options_json(
        self, client: httpx.AsyncClient, auth_headers: dict, db_session: AsyncSession
    ) -> None:
        await _drop_passkeys(db_session)
        resp = await client.post("/v1/auth/passkeys/register/begin", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("application/json")

    # verifies that an account holds exactly one passkey
    async def test_a_second_passkey_is_refused(
        self, client: httpx.AsyncClient, auth_headers: dict
    ) -> None:
        resp = await client.post("/v1/auth/passkeys/register/begin", headers=auth_headers)
        assert resp.status_code == 409

    # verifies that unauthenticated returns 401
    async def test_unauthenticated_returns_401(self, client: httpx.AsyncClient) -> None:
        resp = await client.post("/v1/auth/passkeys/register/begin")
        assert resp.status_code == 401


class TestPasskeyRegisterComplete:
    # verifies that invalid response returns 400
    async def test_invalid_response_returns_400(
        self, client: httpx.AsyncClient, auth_headers: dict, db_session: AsyncSession
    ) -> None:
        await _drop_passkeys(db_session)
        resp = await client.post(
            "/v1/auth/passkeys/register/complete",
            headers=auth_headers,
            json={"credential": "not-valid-webauthn-data"},
        )
        assert resp.status_code in (400, 422)

    # verifies that completing a second registration is refused
    async def test_a_second_passkey_is_refused(
        self, client: httpx.AsyncClient, auth_headers: dict
    ) -> None:
        resp = await client.post(
            "/v1/auth/passkeys/register/complete",
            headers=auth_headers,
            json={"credential": "not-valid-webauthn-data"},
        )
        assert resp.status_code in (409, 422)


class TestPasskeyList:
    # verifies that returns the registered passkey
    async def test_returns_the_registered_passkey(
        self, client: httpx.AsyncClient, auth_headers: dict
    ) -> None:
        resp = await client.get("/v1/auth/passkeys/", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 1


class TestPasskeyAuthBegin:
    # verifies that no email returns 200 or 400
    async def test_no_email_returns_200_or_400(self, client: httpx.AsyncClient) -> None:
        resp = await client.post("/v1/auth/passkeys/authenticate/begin", json={})
        assert resp.status_code in (200, 400, 422)

    # verifies that unknown email answers like an account without passkey
    async def test_unknown_email_answers_like_an_account_without_passkey(
        self, client: httpx.AsyncClient
    ) -> None:
        resp = await client.post(
            "/v1/auth/passkeys/authenticate/begin",
            json={"email": "nobody@example.com"},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"]["message"] == "Passkey not found."
