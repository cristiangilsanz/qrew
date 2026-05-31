from typing import Any

import structlog

from com.qode.qrew.v1.service.core.jobs import job
from com.qode.qrew.v1.service.models.audit.audit import AuditAction
from com.qode.qrew.v1.service.services.audit import AuditChainVerifier, AuditService

logger = structlog.get_logger(__name__)


@job(name="audit.verify_chain", cron="0 3 * * *", max_attempts=1)
async def verify_chain(ctx: dict[str, Any]) -> dict[str, Any]:
    """Recompute the audit hash chain nightly and record the outcome."""
    del ctx
    result = await AuditChainVerifier().verify()
    if result.valid:
        await logger.ainfo("audit_chain_verified", event_count=result.event_count)
        await AuditService().record(
            action=AuditAction.AUDIT_CHAIN_VERIFIED,
            entity_type="system",
            payload={"event_count": result.event_count},
        )
    else:
        await logger.aerror(
            "audit_chain_tampered",
            event_count=result.event_count,
            tampered_ids=result.tampered_ids,
        )
        await AuditService().record(
            action=AuditAction.AUDIT_CHAIN_TAMPERED,
            entity_type="system",
            payload={
                "event_count": result.event_count,
                "tampered_ids": result.tampered_ids,
            },
        )
    return {
        "valid": result.valid,
        "event_count": result.event_count,
        "tampered_ids": result.tampered_ids,
    }
