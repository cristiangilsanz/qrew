import asyncio

import structlog

from com.qode.qrew.v1.audit.models.audit_event import AuditAction
from com.qode.qrew.v1.audit.services.verifier import AuditChainVerifier
from com.qode.qrew.v1.audit.services.writer import AuditService

logger = structlog.get_logger(__name__)

_VERIFY_INTERVAL_SECONDS = 86_400  # 24 hours


async def run_nightly_verify() -> None:
    """Run the chain verifier once every 24 hours, recording the outcome."""
    await asyncio.sleep(3600)  # wait 1 hour after startup before first run
    while True:
        try:
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
        except Exception as exc:
            await logger.awarning("audit_verify.failed", error=repr(exc))
        await asyncio.sleep(_VERIFY_INTERVAL_SECONDS)
