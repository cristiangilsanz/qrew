from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import or_, select, update

from com.qode.qrew.v1.service.core.infra.database import AsyncSessionLocal
from com.qode.qrew.v1.service.core.jobs import job
from com.qode.qrew.v1.service.core.storage import storage
from com.qode.qrew.v1.service.models.audit.audit import AuditAction
from com.qode.qrew.v1.service.models.auth.user import KycStatus, User
from com.qode.qrew.v1.service.services.audit import AuditService
from com.qode.qrew.v1.service.settings import settings

logger = structlog.get_logger(__name__)


@job(name="storage.kyc_retention", cron="0 4 * * *", max_attempts=1)
async def purge_old_kyc_documents(ctx: dict[str, Any]) -> dict[str, int]:
    """Delete KYC documents older than the configured retention window."""
    del ctx
    days = settings.kyc_document_retention_days
    cutoff = datetime.now(UTC) - timedelta(days=days)
    deleted = 0
    keys_to_clear: list[tuple[str, str]] = []

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User.id, User.kyc_document_object_key).where(
                User.kyc_document_object_key.is_not(None),
                or_(
                    (User.kyc_status == KycStatus.rejected)
                    & (User.updated_at < cutoff),
                    User.deleted_at.is_not(None) & (User.deleted_at < cutoff),
                ),
            )
        )
        rows = result.all()
        for user_id, object_key in rows:
            if not isinstance(object_key, str):
                continue
            try:
                await storage.delete(object_key)
                deleted += 1
                keys_to_clear.append((str(user_id), object_key))
            except Exception:
                await logger.awarning(
                    "kyc_retention_delete_failed",
                    user_id=str(user_id),
                    object_key=object_key,
                )

    if keys_to_clear:
        async with AsyncSessionLocal() as session, session.begin():
            ids = [user_id for user_id, _ in keys_to_clear]
            await session.execute(
                update(User)
                .where(User.id.in_(ids))
                .values(kyc_document_object_key=None)
            )

    await logger.ainfo("kyc_retention_completed", deleted=deleted, cutoff=str(cutoff))
    if deleted > 0:
        try:
            await AuditService().record(
                action=AuditAction.EXPIRED_TOKENS_CLEANED,
                entity_type="system",
                payload={
                    "summary": "kyc_document_retention",
                    "deleted": deleted,
                    "retention_days": days,
                },
            )
        except Exception:
            await logger.awarning("kyc_retention_audit_write_failed")
    return {"deleted": deleted}
