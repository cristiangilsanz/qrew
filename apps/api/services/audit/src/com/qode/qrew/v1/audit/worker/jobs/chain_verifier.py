# schedules a nightly verification of the audit hash chain
import asyncio

import structlog

from com.qode.qrew.v1.audit.services import AuditAction, AuditChainVerifier, AuditService

logger = structlog.get_logger(__name__)

_VERIFY_INTERVAL_SECONDS = 86_400


# verifies the chain once a day and records the outcome
async def run_nightly_verify() -> None:
    await asyncio.sleep(3600)
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
