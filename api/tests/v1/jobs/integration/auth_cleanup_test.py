import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from com.qode.qrew.v1.service.core.infra.database import AsyncSessionLocal
from com.qode.qrew.v1.service.jobs.auth_cleanup import cleanup_expired_tokens
from com.qode.qrew.v1.service.models.auth.user import KycStatus, User


@pytest.mark.integration
async def test_cleanup_clears_expired_tokens() -> None:
    suffix = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as session, session.begin():
        user = User(
            hashed_password="x",
            email_verification_token="expired-token",
            email_verification_token_expires_at=datetime.now(UTC) - timedelta(hours=1),
            phone_number_otp="999999",
            phone_number_otp_expires_at=datetime.now(UTC) - timedelta(minutes=5),
            terms_accepted_at=datetime.now(UTC),
            registration_ip="127.0.0.1",
            kyc_status=KycStatus.not_submitted,
        )
        user.email = f"cleanup-{suffix}@example.com"
        user.phone_number = "+34600000000"
        user.full_name = "Cleanup Test"
        session.add(user)

    result = await cleanup_expired_tokens({})
    assert result["cleared"] >= 2

    async with AsyncSessionLocal() as session:
        rows = await session.execute(
            select(User).where(User.email_hash == user.email_hash)
        )
        refreshed = rows.scalar_one()
        assert refreshed.email_verification_token is None
        assert refreshed.phone_number_otp is None
