# projects catalog's events and rosters into the entry service's local context
import asyncio
import contextlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from messaging.client import get_nats
from observability import traced_message
from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert

from com.qode.qrew.v1.entry.core.database import AsyncSessionLocal
from com.qode.qrew.v1.entry.models.projections import (
    EventContext,
    OrganisationMemberContext,
)

logger = structlog.get_logger(__name__)

STREAM = "CATALOG"
EVENT_SUBJECTS = (
    "catalog.event.published.v1",
    "catalog.event.updated.v1",
    "catalog.event.ongoing.v1",
)
MEMBERSHIP_SUBJECT = "catalog.membership.changed.v1"


# reads the envelope a subject carries, or nothing when it arrives malformed
async def _parse(msg: Any) -> dict[str, Any] | None:
    try:
        body = json.loads(msg.data.decode())
        assert isinstance(body, dict)
        data: Any = body["data"]  # pyright: ignore[reportUnknownVariableType]
        assert isinstance(data, dict)
        return data  # type: ignore[return-value]
    except Exception as exc:
        await logger.awarning("catalog_projector.invalid_message", error=repr(exc))
        return None


# remembers which organisation and venue an event belongs to
@traced_message()
async def handle_event(msg: Any) -> None:
    data = await _parse(msg)
    if data is None:
        return
    try:
        event_id = uuid.UUID(str(data["event_id"]))
        organisation_id = uuid.UUID(str(data["organisation_id"]))
    except (KeyError, ValueError):
        await logger.awarning("catalog_projector.event_missing_fields")
        return
    venue_raw = data.get("venue_id")
    venue_id = uuid.UUID(str(venue_raw)) if venue_raw else None

    async with AsyncSessionLocal() as session, session.begin():
        stmt = insert(EventContext).values(
            event_id=event_id,
            organisation_id=organisation_id,
            venue_id=venue_id,
            updated_at=datetime.now(UTC),
        )
        await session.execute(
            stmt.on_conflict_do_update(
                index_elements=[EventContext.event_id],
                set_={
                    "organisation_id": organisation_id,
                    "venue_id": venue_id,
                    "updated_at": datetime.now(UTC),
                },
            )
        )
    await logger.ainfo("catalog_projector.event", event_id=str(event_id))


# remembers who belongs to an organisation, and forgets whoever leaves it
@traced_message(MEMBERSHIP_SUBJECT)
async def handle_membership(msg: Any) -> None:
    data = await _parse(msg)
    if data is None:
        return
    try:
        organisation_id = uuid.UUID(str(data["organisation_id"]))
        user_id = uuid.UUID(str(data["user_id"]))
    except (KeyError, ValueError):
        await logger.awarning("catalog_projector.membership_missing_fields")
        return
    role = data.get("role")

    async with AsyncSessionLocal() as session, session.begin():
        if role is None:
            await session.execute(
                delete(OrganisationMemberContext).where(
                    OrganisationMemberContext.organisation_id == organisation_id,
                    OrganisationMemberContext.user_id == user_id,
                )
            )
        else:
            stmt = insert(OrganisationMemberContext).values(
                organisation_id=organisation_id,
                user_id=user_id,
                role=str(role),
                updated_at=datetime.now(UTC),
            )
            await session.execute(
                stmt.on_conflict_do_update(
                    index_elements=[
                        OrganisationMemberContext.organisation_id,
                        OrganisationMemberContext.user_id,
                    ],
                    set_={"role": str(role), "updated_at": datetime.now(UTC)},
                )
            )
    await logger.ainfo(
        "catalog_projector.membership", organisation_id=str(organisation_id)
    )


# subscribes to the catalog subjects the entry service projects
async def run_catalog_projector() -> None:
    nc = get_nats()
    js = nc.js
    try:
        try:
            await js.find_stream_name_by_subject("catalog.>")
        except Exception:
            await js.add_stream(  # pyright: ignore[reportUnknownMemberType]
                name=STREAM, subjects=["catalog.>"]
            )
        for subject in EVENT_SUBJECTS:
            await js.subscribe(
                subject,
                cb=handle_event,
                durable=f"entry-catalog-{subject.replace('.', '-')}",
            )
        await js.subscribe(
            MEMBERSHIP_SUBJECT, cb=handle_membership, durable="entry-catalog-membership"
        )
        await logger.ainfo("catalog_projector.subscribed")
    except Exception as exc:
        await logger.awarning("catalog_projector.subscribe_failed", error=repr(exc))
        return

    with contextlib.suppress(asyncio.CancelledError):
        await asyncio.Event().wait()
