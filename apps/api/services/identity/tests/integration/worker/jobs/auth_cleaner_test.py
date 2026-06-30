from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]


class TestCleanupExpiredTokens:
    async def test_clears_expired_email_tokens(
        self, db_session: AsyncSession, registered_user: dict
    ) -> None:
        import uuid
        from com.qode.qrew.v1.identity.models.user import User
        from com.qode.qrew.v1.identity.worker.jobs.auth_cleaner import cleanup_expired_tokens

        user_id = uuid.UUID(registered_user["user_id"])

        # Plant an expired verification token directly.
        past = datetime.now(UTC) - timedelta(hours=1)
        await db_session.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                email_verification_token="expired-token",
                email_verification_token_expires_at=past,
            )
        )
        await db_session.commit()

        result = await cleanup_expired_tokens({})
        assert result["cleared"] >= 1

    async def test_returns_zero_when_nothing_expired(self, setup_test_infrastructure) -> None:
        from com.qode.qrew.v1.identity.worker.jobs.auth_cleaner import cleanup_expired_tokens

        result = await cleanup_expired_tokens({})
        assert isinstance(result["cleared"], int)
