import uuid

import httpx
import pytest
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]


async def _user_with_pending_kyc(client: httpx.AsyncClient, db_session: AsyncSession) -> str:
    """Register a user and set their KYC status to pending directly in DB."""
    from com.qode.qrew.v1.identity.models.user import KycStatus, User

    email = f"kyc-{uuid.uuid4().hex[:8]}@example.com"
    phone = f"+316{str(int(uuid.uuid4().int % 9_000_000) + 1_000_000)}"
    resp = await client.post(
        "/v1/auth/registration/",
        json={
            "full_name": "KYC User",
            "email": email,
            "phone_number": phone,
            "password": "StrongP@ss1!",
            "terms_accepted": True,
            "captcha_token": "test-token",
        },
    )
    user_id = uuid.UUID(resp.json()["id"])
    await db_session.execute(
        update(User)
        .where(User.id == user_id)
        .values(kyc_status=KycStatus.pending, email_verified=True)
    )
    await db_session.commit()
    return str(user_id)


class TestKycReview:
    async def test_approve_pending_user(
        self,
        client: httpx.AsyncClient,
        db_session: AsyncSession,
        admin_headers: dict,
    ) -> None:
        user_id = await _user_with_pending_kyc(client, db_session)
        resp = await client.post(
            f"/v1/admin/kyc/{user_id}/review",
            headers=admin_headers,
            json={"action": "approve", "reason": None},
        )
        assert resp.status_code == 200
        assert resp.json()["kyc_status"] == "approved"

    async def test_reject_pending_user(
        self,
        client: httpx.AsyncClient,
        db_session: AsyncSession,
        admin_headers: dict,
    ) -> None:
        user_id = await _user_with_pending_kyc(client, db_session)
        resp = await client.post(
            f"/v1/admin/kyc/{user_id}/review",
            headers=admin_headers,
            json={"action": "reject", "reason": "document unclear"},
        )
        assert resp.status_code == 200
        assert resp.json()["kyc_status"] == "rejected"

    async def test_nonexistent_user_returns_400(
        self, client: httpx.AsyncClient, admin_headers: dict
    ) -> None:
        resp = await client.post(
            f"/v1/admin/kyc/{uuid.uuid4()}/review",
            headers=admin_headers,
            json={"action": "approve", "reason": None},
        )
        assert resp.status_code == 400

    async def test_non_admin_returns_403(
        self, client: httpx.AsyncClient, auth_headers: dict
    ) -> None:
        resp = await client.post(
            f"/v1/admin/kyc/{uuid.uuid4()}/review",
            headers=auth_headers,
            json={"action": "approve", "reason": None},
        )
        assert resp.status_code == 403

    async def test_unauthenticated_returns_401(self, client: httpx.AsyncClient) -> None:
        resp = await client.post(
            f"/v1/admin/kyc/{uuid.uuid4()}/review",
            json={"action": "approve", "reason": None},
        )
        assert resp.status_code == 401
