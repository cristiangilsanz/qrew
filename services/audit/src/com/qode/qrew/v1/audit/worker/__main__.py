"""Entry point for the audit worker process that consumes events and runs scheduled verification."""

import asyncio

import structlog

from worker import run_nats_subscribers
from com.qode.qrew.v1.audit.services.writer import AuditService
from com.qode.qrew.v1.audit.core.config import settings
from com.qode.qrew.v1.audit.worker.jobs.verify_chain import run_nightly_verify
from com.qode.qrew.v1.audit.worker.events import run_audit_event_subscriber

logger = structlog.get_logger(__name__)


async def main() -> None:
    await logger.ainfo("audit_worker.startup")
    await AuditService().ensure_genesis()

    await run_nats_subscribers(
        "audit",
        run_audit_event_subscriber(settings.nats_url),
        run_nightly_verify(),
    )


if __name__ == "__main__":
    asyncio.run(main())
