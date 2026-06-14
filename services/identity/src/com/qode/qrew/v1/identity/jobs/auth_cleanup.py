from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import update

from com.qode.qrew.v1.identity.core.infra.database import AsyncSessionLocal
from com.qode.qrew.v1.identity.core.jobs import job
from com.qode.qrew.v1.identity.models.audit.audit import AuditAction
from com.qode.qrew.v1.identity.models.auth.user import User
from com.qode.qrew.v1.identity.services.audit import AuditService

logger = structlog.get_logger(__name__)


@job(name="auth.cleanup_expired_tokens", cron="*/15 * * * *", max_attempts=3)
async def cleanup_expired_tokens(ctx: dict[str, Any]) -> dict[str, int]:
    """Null out expired verification tokens and OTPs to keep the users table tidy."""
    del ctx
    now = datetime.now(UTC)
    cleared = 0
    async with AsyncSessionLocal() as session, session.begin():
        result = await session.execute(
            update(User)
            .where(User.email_verification_token_expires_at < now)
            .where(User.email_verification_token.is_not(None))
            .values(
                email_verification_token=None,
                email_verification_token_expires_at=None,
            )
        )
        cleared += int(getattr(result, "rowcount", 0) or 0)

        result = await session.execute(
            update(User)
            .where(User.phone_number_otp_expires_at < now)
            .where(User.phone_number_otp.is_not(None))
            .values(
                phone_number_otp=None,
                phone_number_otp_expires_at=None,
            )
        )
        cleared += int(getattr(result, "rowcount", 0) or 0)

        result = await session.execute(
            update(User)
            .where(User.pending_phone_otp_expires_at < now)
            .where(User.pending_phone_otp.is_not(None))
            .values(
                pending_phone_otp=None,
                pending_phone_otp_expires_at=None,
                pending_phone_number_ciphertext=None,
                pending_phone_number_hash=None,
            )
        )
        cleared += int(getattr(result, "rowcount", 0) or 0)

        result = await session.execute(
            update(User)
            .where(User.pending_email_token_expires_at < now)
            .where(User.pending_email_verification_token.is_not(None))
            .values(
                pending_email_verification_token=None,
                pending_email_token_expires_at=None,
                pending_email_ciphertext=None,
                pending_email_hash=None,
            )
        )
        cleared += int(getattr(result, "rowcount", 0) or 0)

    await logger.ainfo("auth_tokens_cleaned", cleared=cleared)
    if cleared > 0:
        await AuditService().record(
            action=AuditAction.EXPIRED_TOKENS_CLEANED,
            entity_type="system",
            payload={"cleared_rows": cleared},
        )
    return {"cleared": cleared}
