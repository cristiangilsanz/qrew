import re
import uuid
from datetime import UTC, datetime, timezone
from typing import Any

import structlog

from com.qode.qrew.v1.catalog.core.audit import AuditService
from com.qode.qrew.v1.catalog.core.infra.errors import DomainError
from com.qode.qrew.v1.catalog.core.locking import redlock
from com.qode.qrew.v1.catalog.core.observability import traced
from com.qode.qrew.v1.catalog.models.event import EventStatus
from com.qode.qrew.v1.catalog.models.ticket_type import TicketType
from com.qode.qrew.v1.catalog.repositories.event import EventRepository
from com.qode.qrew.v1.catalog.repositories.ticket_type import TicketTypeRepository

logger = structlog.get_logger(__name__)


async def _publish_nats(subject: str, ticket_type: TicketType) -> None:
    try:
        from common.broker.publisher import publish  # type: ignore[import-not-found]
        from common.events.envelope import EventEnvelope  # type: ignore[import-not-found]

        envelope = EventEnvelope(
            occurred_at=datetime.now(UTC),
            aggregate_type="ticket_type",
            aggregate_id=str(ticket_type.id),
            data={
                "ticket_type_id": str(ticket_type.id),
                "event_id": str(ticket_type.event_id),
                "capacity": ticket_type.capacity,
                "price_cents": ticket_type.price_cents,
                "currency": ticket_type.currency,
            },
        )
        await publish(subject, envelope)
    except Exception as exc:
        await logger.awarning("nats_publish_failed", subject=subject, error=repr(exc))

_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,31}$")
ALLOWED_CURRENCIES: frozenset[str] = frozenset({"EUR", "USD", "GBP"})
_MUTABLE_FIELDS: frozenset[str] = frozenset(
    {"name", "description", "price_cents", "position", "capacity"}
)


class TicketTypeError(DomainError):
    pass


def _validate_name(name: str) -> None:
    if not _NAME_PATTERN.match(name):
        raise TicketTypeError(
            "Name must be lowercase letters, digits or underscores", field="name"
        )


def _validate_capacity(capacity: int) -> None:
    if capacity < 1 or capacity > 100_000:
        raise TicketTypeError("Capacity must be between 1 and 100000", field="capacity")


def _validate_price(price_cents: int) -> None:
    if price_cents < 0 or price_cents > 10_000_000:
        raise TicketTypeError(
            "Price must be between 0 and 10000000 cents", field="price_cents"
        )


def _validate_currency(currency: str) -> None:
    if currency not in ALLOWED_CURRENCIES:
        raise TicketTypeError(
            f"Currency must be one of {sorted(ALLOWED_CURRENCIES)}", field="currency"
        )


class TicketTypeService:
    def __init__(
        self,
        event_repo: EventRepository,
        repo: TicketTypeRepository,
        audit: AuditService,
    ) -> None:
        self._event_repo = event_repo
        self._repo = repo
        self._audit = audit

    @traced("ticket_type.create")
    async def create(
        self,
        *,
        actor_id: uuid.UUID,
        event_id: uuid.UUID,
        name: str,
        description: str | None,
        capacity: int,
        price_cents: int,
        currency: str,
        position: int,
    ) -> TicketType:
        _validate_name(name)
        _validate_capacity(capacity)
        _validate_price(price_cents)
        _validate_currency(currency)
        async with redlock(f"event:{event_id}:ticket-types", ttl_seconds=10):
            event = await self._event_repo.get_by_id(event_id)
            if event is None:
                raise TicketTypeError("Event not found", field="event_id")
            if event.status == EventStatus.cancelled:
                raise TicketTypeError(
                    "Cannot add ticket types to a cancelled event", field="status"
                )
            existing = await self._repo.get_by_event_and_name(event_id, name)
            if existing is not None:
                raise TicketTypeError(
                    "A ticket type with that name already exists", field="name"
                )
            ticket_type = TicketType(
                event_id=event_id,
                name=name,
                description=description,
                capacity=capacity,
                reserved_count=0,
                price_cents=price_cents,
                currency=currency,
                position=position,
            )
            ticket_type = await self._repo.insert(ticket_type)
            await self._record(
                "ticket_type_created",
                actor_id=actor_id,
                ticket_type_id=ticket_type.id,
                payload={"event_id": str(event_id), "name": name},
            )
            await _publish_nats("catalog.ticket_type.created.v1", ticket_type)
            return ticket_type

    @traced("ticket_type.update")
    async def update(
        self,
        *,
        actor_id: uuid.UUID,
        event_id: uuid.UUID,
        ticket_type_id: uuid.UUID,
        changes: dict[str, Any],
    ) -> TicketType:
        unknown = set(changes) - _MUTABLE_FIELDS
        if unknown:
            raise TicketTypeError(f"Cannot edit fields: {sorted(unknown)}", field=None)
        async with redlock(f"event:{event_id}:ticket-types", ttl_seconds=10):
            ticket_type = await self._repo.get_by_id(ticket_type_id)
            if ticket_type is None or ticket_type.event_id != event_id:
                raise TicketTypeError("Ticket type not found", field="ticket_type_id")
            if "name" in changes:
                _validate_name(changes["name"])
                if changes["name"] != ticket_type.name:
                    conflict = await self._repo.get_by_event_and_name(
                        event_id, changes["name"]
                    )
                    if conflict is not None and conflict.id != ticket_type.id:
                        raise TicketTypeError(
                            "A ticket type with that name already exists", field="name"
                        )
            if "capacity" in changes:
                _validate_capacity(changes["capacity"])
                if changes["capacity"] < ticket_type.capacity:
                    raise TicketTypeError(
                        "Capacity can only increase; "
                        "lower it by soft-deleting and re-creating the tier",
                        field="capacity",
                    )
            if "price_cents" in changes:
                _validate_price(changes["price_cents"])
            for key, value in changes.items():
                setattr(ticket_type, key, value)
            await self._repo.flush()
            await self._record(
                "ticket_type_updated",
                actor_id=actor_id,
                ticket_type_id=ticket_type.id,
                payload={"fields": sorted(changes.keys())},
            )
            await _publish_nats("catalog.ticket_type.updated.v1", ticket_type)
            return ticket_type

    @traced("ticket_type.delete")
    async def delete(
        self,
        *,
        actor_id: uuid.UUID,
        event_id: uuid.UUID,
        ticket_type_id: uuid.UUID,
    ) -> None:
        async with redlock(f"event:{event_id}:ticket-types", ttl_seconds=10):
            ticket_type = await self._repo.get_by_id(ticket_type_id)
            if ticket_type is None or ticket_type.event_id != event_id:
                raise TicketTypeError("Ticket type not found", field="ticket_type_id")
            if ticket_type.reserved_count > 0:
                raise TicketTypeError(
                    "Cannot delete a tier with live reservations", field="reserved_count"
                )
            ticket_type.deleted_at = datetime.now(timezone.utc)
            await self._repo.flush()
            await self._record(
                "ticket_type_deleted",
                actor_id=actor_id,
                ticket_type_id=ticket_type.id,
                payload={"event_id": str(event_id)},
            )

    async def _record(
        self,
        action: str,
        *,
        actor_id: uuid.UUID,
        ticket_type_id: uuid.UUID,
        payload: dict[str, Any],
    ) -> None:
        try:
            await self._audit.record(
                action=action,
                actor_id=actor_id,
                entity_type="ticket_type",
                entity_id=str(ticket_type_id),
                payload=payload,
            )
        except Exception:
            await logger.awarning("audit_write_failed", action=action)
