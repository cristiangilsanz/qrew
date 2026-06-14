"""Audit NATS worker process: subscribes to audit.events.v1 and runs nightly verify."""

import asyncio

import structlog

from com.qode.qrew.v1.audit.services.writer import AuditService
from com.qode.qrew.v1.audit.settings import settings

logger = structlog.get_logger(__name__)


async def main() -> None:
    await logger.ainfo("audit_worker.startup")
    await AuditService().ensure_genesis()

    nats_url = settings.nats_url
    if not nats_url:
        await logger.awarning("audit_worker.no_nats_url")
        return

    from com.qode.qrew.v1.audit.jobs.verify_chain import run_nightly_verify
    from com.qode.qrew.v1.audit.worker.events import run_audit_event_subscriber

    await asyncio.gather(
        run_audit_event_subscriber(nats_url),
        run_nightly_verify(),
    )


if __name__ == "__main__":
    asyncio.run(main())
