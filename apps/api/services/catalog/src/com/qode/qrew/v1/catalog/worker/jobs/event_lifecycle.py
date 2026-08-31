# moves published events into their ongoing state once their start time arrives
from typing import Any

import structlog
from sqlalchemy import text

from jobs import job, parse_crontab
from com.qode.qrew.v1.catalog.core.database import AsyncSessionLocal
from com.qode.qrew.v1.catalog.repositories.events.event import EventRepository
from com.qode.qrew.v1.catalog.repositories.organisation import OrganisationRepository
from com.qode.qrew.v1.catalog.repositories.venue import VenueRepository
from com.qode.qrew.v1.catalog.services.application.audit import AuditService
from com.qode.qrew.v1.catalog.services.application.events.event import EventError, EventService

logger = structlog.get_logger(__name__)

_DUE_EVENTS = text(
    "SELECT id FROM catalog.events WHERE status = 'published' AND starts_at <= now()"
)


# starts every published event whose start time has already passed
@job("events.start_due", cron=parse_crontab("* * * * *"), max_attempts=1)
async def start_due_events(ctx: dict[str, Any]) -> dict[str, Any]:
    del ctx
    async with AsyncSessionLocal() as session:
        due = list((await session.execute(_DUE_EVENTS)).scalars())

    started = 0
    for event_id in due:
        async with AsyncSessionLocal() as session, session.begin():
            service = EventService(
                session,
                EventRepository(session),
                OrganisationRepository(session),
                VenueRepository(session),
                AuditService(),
            )
            try:
                await service.start_event(actor_id=None, event_id=event_id)
            except EventError as exc:
                await logger.awarning(
                    "events.start_due.skipped", event_id=str(event_id), reason=str(exc)
                )
                continue
        started += 1

    if started:
        await logger.ainfo("events.start_due", started=started, due=len(due))
    return {"due": len(due), "started": started}
