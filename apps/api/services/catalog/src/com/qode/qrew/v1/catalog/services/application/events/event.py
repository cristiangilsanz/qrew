import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import Select, text
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.catalog.services.application.audit import AuditService
from com.qode.qrew.v1.catalog.core.errors import DomainError
from locking import redlock
from com.qode.qrew.v1.catalog.core.config import settings
from observability import traced
from com.qode.qrew.v1.catalog.repositories.events.search.tsvector import update_one_sql
from com.qode.qrew.v1.catalog.models.event import Event, EventStatus
from com.qode.qrew.v1.catalog.models.organisation import Organisation
from com.qode.qrew.v1.catalog.models.venue import Venue
from com.qode.qrew.v1.catalog.repositories.events.event import EventRepository
from com.qode.qrew.v1.catalog.repositories.organisation import OrganisationRepository
from com.qode.qrew.v1.catalog.repositories.venue import VenueRepository
from com.qode.qrew.v1.catalog.repositories.events.search.events import EVENTS_SEARCH_CONFIG

logger = structlog.get_logger(__name__)

_MUTABLE_FIELDS: frozenset[str] = frozenset(
    {
        "name",
        "description",
        "starts_at",
        "ends_at",
        "sale_starts_at",
        "sale_ends_at",
        "max_tickets_per_user",
        "queue_required",
        "queue_admit_rate_per_minute",
    }
)


class EventError(DomainError):
    pass


def _validate_windows(
    *,
    starts_at: datetime,
    ends_at: datetime,
    sale_starts_at: datetime,
    sale_ends_at: datetime,
) -> None:
    if starts_at >= ends_at:
        raise EventError("Event must start before it ends", field="starts_at")
    if sale_starts_at >= sale_ends_at:
        raise EventError("Sale must start before it ends", field="sale_starts_at")
    if sale_ends_at > starts_at:
        raise EventError("Sale must close before the event starts", field="sale_ends_at")


def _validate_max_tickets(value: int) -> None:
    if value < 1 or value > 20:
        raise EventError(
            "max_tickets_per_user must be between 1 and 20",
            field="max_tickets_per_user",
        )


async def _publish_nats(
    subject: str, aggregate_type: str, aggregate_id: str, data: dict[str, Any]
) -> None:
    try:
        from messaging.publisher import publish  # type: ignore[import-not-found]
        from contracts.messaging.envelope import EventEnvelope  # type: ignore[import-not-found]

        envelope = EventEnvelope(
            occurred_at=datetime.now(UTC),
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            data=data,
        )
        await publish(subject, envelope)
    except Exception as exc:
        await logger.awarning("nats_publish_failed", subject=subject, error=repr(exc))


class EventService:
    def __init__(
        self,
        session: AsyncSession,
        repo: EventRepository,
        org_repo: OrganisationRepository,
        venue_repo: VenueRepository,
        audit: AuditService,
    ) -> None:
        self._session = session
        self._repo = repo
        self._org_repo = org_repo
        self._venue_repo = venue_repo
        self._audit = audit

    def list_for_org_query(self, organisation_id: uuid.UUID) -> Select[tuple[Event]]:
        return self._repo.list_for_org_query(organisation_id)

    async def get_by_id(self, event_id: uuid.UUID) -> Event | None:
        return await self._repo.get_by_id(event_id)

    async def _load_organisation(self, organisation_id: uuid.UUID) -> Organisation:
        org = await self._org_repo.get_by_id(organisation_id)
        if org is None:
            raise EventError("Organisation not found", field="organisation_id")
        return org

    async def _load_venue(self, venue_id: uuid.UUID) -> Venue:
        venue = await self._venue_repo.get_by_id(venue_id)
        if venue is None:
            raise EventError("Venue not found", field="venue_id")
        return venue

    async def _reindex(self, event_id: uuid.UUID) -> None:
        await self._session.execute(
            text(update_one_sql(EVENTS_SEARCH_CONFIG)),
            {"row_id": str(event_id)},
        )

    @traced("event.create")
    async def create_event(
        self,
        *,
        actor_id: uuid.UUID,
        organisation_id: uuid.UUID,
        venue_id: uuid.UUID,
        name: str,
        description: str | None,
        starts_at: datetime,
        ends_at: datetime,
        sale_starts_at: datetime,
        sale_ends_at: datetime,
        max_tickets_per_user: int,
    ) -> Event:
        _validate_windows(
            starts_at=starts_at,
            ends_at=ends_at,
            sale_starts_at=sale_starts_at,
            sale_ends_at=sale_ends_at,
        )
        _validate_max_tickets(max_tickets_per_user)
        org = await self._load_organisation(organisation_id)
        venue = await self._load_venue(venue_id)
        event = Event(
            organisation_id=org.id,
            venue_id=venue.id,
            name=name,
            description=description,
            starts_at=starts_at,
            ends_at=ends_at,
            sale_starts_at=sale_starts_at,
            sale_ends_at=sale_ends_at,
            max_tickets_per_user=max_tickets_per_user,
            status=EventStatus.draft,
            organiser_name=org.name,
            venue_city=venue.city,
        )
        event = await self._repo.insert(event)
        await self._record(
            "event_created",
            actor_id=actor_id,
            event_id=event.id,
            payload={"name": event.name, "organisation_id": str(org.id)},
        )
        return event

    @traced("event.update")
    async def update_event(
        self,
        *,
        actor_id: uuid.UUID,
        event_id: uuid.UUID,
        changes: dict[str, Any],
    ) -> Event:
        event = await self._repo.get_by_id(event_id)
        if event is None:
            raise EventError("Event not found", field="event_id")
        if event.status != EventStatus.draft:
            raise EventError("Only draft events can be edited", field="status")
        unknown = set(changes) - _MUTABLE_FIELDS
        if unknown:
            raise EventError(f"Cannot edit fields: {sorted(unknown)}", field=None)
        for key, value in changes.items():
            setattr(event, key, value)
        _validate_windows(
            starts_at=event.starts_at,
            ends_at=event.ends_at,
            sale_starts_at=event.sale_starts_at,
            sale_ends_at=event.sale_ends_at,
        )
        _validate_max_tickets(event.max_tickets_per_user)
        await self._repo.flush()
        await self._record(
            "event_updated",
            actor_id=actor_id,
            event_id=event.id,
            payload={"fields": sorted(changes.keys())},
        )
        return event

    @traced("event.publish")
    async def publish_event(self, *, actor_id: uuid.UUID, event_id: uuid.UUID) -> Event:
        async with redlock(
            f"event:{event_id}:lifecycle", redis_url=settings.redis_url, ttl_seconds=10
        ):
            event = await self._repo.get_by_id(event_id)
            if event is None:
                raise EventError("Event not found", field="event_id")
            if event.status == EventStatus.published:
                return event
            if event.status != EventStatus.draft:
                raise EventError("Only draft events can be published", field="status")
            event.status = EventStatus.published
            event.published_at = datetime.now(UTC)
            await self._repo.flush()
            await self._reindex(event.id)
            await self._record(
                "event_published",
                actor_id=actor_id,
                event_id=event.id,
                payload={"organisation_id": str(event.organisation_id)},
            )
            await _publish_nats(
                "catalog.event.published.v1",
                aggregate_type="event",
                aggregate_id=str(event.id),
                data={"event_id": str(event.id), "organisation_id": str(event.organisation_id)},
            )
            return event

    @traced("event.cancel")
    async def cancel_event(self, *, actor_id: uuid.UUID, event_id: uuid.UUID) -> Event:
        async with redlock(
            f"event:{event_id}:lifecycle", redis_url=settings.redis_url, ttl_seconds=10
        ):
            event = await self._repo.get_by_id(event_id)
            if event is None:
                raise EventError("Event not found", field="event_id")
            if event.status == EventStatus.cancelled:
                return event
            event.status = EventStatus.cancelled
            event.cancelled_at = datetime.now(UTC)
            await self._repo.flush()
            await self._reindex(event.id)
            await self._record(
                "event_cancelled",
                actor_id=actor_id,
                event_id=event.id,
                payload={"organisation_id": str(event.organisation_id)},
            )
            await _publish_nats(
                "catalog.event.cancelled.v1",
                aggregate_type="event",
                aggregate_id=str(event.id),
                data={
                    "event_id": str(event.id),
                    "organisation_id": str(event.organisation_id),
                },
            )
            return event

    async def _record(
        self,
        action: str,
        *,
        actor_id: uuid.UUID,
        event_id: uuid.UUID,
        payload: dict[str, Any],
    ) -> None:
        try:
            await self._audit.record(
                action=action,
                actor_id=actor_id,
                entity_type="event",
                entity_id=str(event_id),
                payload=payload,
            )
        except Exception as exc:
            await logger.awarning("audit_write_failed", action=action, error=repr(exc))
