# reserves tickets against the fraud check the queue and the ticket type inventory
import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from collections.abc import Sequence
from typing import Any

import structlog
from jwt import InvalidTokenError
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.sales.services.application.audit import AuditService
from com.qode.qrew.v1.sales.services.application.queue.storage import consume_reservation_token
from com.qode.qrew.v1.sales.core.errors import DomainError
from locking import redlock
from observability import traced
from com.qode.qrew.v1.sales.models.projections import TicketTypeInventory
from com.qode.qrew.v1.sales.models.reservation import Reservation, ReservationStatus
from com.qode.qrew.v1.sales.models.reservation_item import ReservationItem
from com.qode.qrew.v1.sales.repositories.projections import (
    EventContextRepository,
    TicketTypeInventoryRepository,
)
from com.qode.qrew.v1.sales.repositories.reservation import ReservationRepository
from com.qode.qrew.v1.sales.services.domain.fraud.context import PurchaseContext
from com.qode.qrew.v1.sales.services.domain.fraud.dependencies import build_engine_for_user
from com.qode.qrew.v1.sales.services.domain.fraud.engine import FraudDecision
from com.qode.qrew.v1.sales.core.config import settings

logger = structlog.get_logger(__name__)

_RESERVATION_CREATED = "RESERVATION_CREATED"
_RESERVATION_CANCELLED = "RESERVATION_CANCELLED"

_NATS_PUBLISH_TIMEOUT = 5.0


class ReservationError(DomainError):
    pass


class TierBusyError(DomainError):
    pass


class FraudBlockedError(DomainError):
    pass


# returns the current time
def _now() -> datetime:
    return datetime.now(UTC)


class ReservationService:
    # stores the session repositories and audit service the service uses
    def __init__(
        self,
        session: AsyncSession,
        repo: ReservationRepository,
        event_ctx_repo: EventContextRepository,
        inventory_repo: TicketTypeInventoryRepository,
        audit: AuditService,
    ) -> None:
        self._session = session
        self._repo = repo
        self._event_ctx_repo = event_ctx_repo
        self._inventory_repo = inventory_repo
        self._audit = audit

    # locks a ticket type's inventory row without waiting for a rival caller
    async def _lock_inventory_nowait(self, ticket_type_id: uuid.UUID) -> TicketTypeInventory | None:
        try:
            return await self._session.get(
                TicketTypeInventory,
                ticket_type_id,
                with_for_update={"nowait": True},
                populate_existing=True,
            )
        except DBAPIError as exc:
            raise TierBusyError(
                "Ticket type busy.",
                field="ticket_type_id",
            ) from exc

    # scores the purchase for fraud and reserves tickets within the event's limits
    @traced("reservation.create")
    async def reserve(
        self,
        *,
        user_id: uuid.UUID,
        event_id: uuid.UUID,
        items: Sequence[tuple[uuid.UUID, int]],
        ip_address: str | None = None,
        fingerprint_hash: str | None = None,
        reservation_window_token: str | None = None,
    ) -> tuple[Reservation, list[ReservationItem]]:
        if not items:
            raise ReservationError("Ticket types missing.", field="items")
        if any(quantity < 1 for _, quantity in items):
            raise ReservationError("Quantity must be at least 1.", field="quantity")
        if len({ticket_type_id for ticket_type_id, _ in items}) != len(items):
            raise ReservationError("Ticket type repeated.", field="items")
        total_quantity = sum(quantity for _, quantity in items)

        engine = await build_engine_for_user(
            self._session, user_id=user_id, fingerprint_hash=fingerprint_hash
        )
        evaluation = await engine.evaluate(
            PurchaseContext(
                user_id=user_id,
                ip_address=ip_address,
                device_fingerprint_hash=fingerprint_hash,
                now=_now(),
            )
        )

        if evaluation.decision == FraudDecision.block:
            await self._record_blocked(
                actor_id=user_id, event_id=event_id, payload=evaluation.to_payload()
            )
            raise FraudBlockedError("Reservation rejected.")

        if reservation_window_token is not None:
            try:
                token_event = await consume_reservation_token(
                    token=reservation_window_token, user_id=user_id
                )
            except InvalidTokenError as exc:
                raise ReservationError(
                    "Reservation window token is invalid", field="reservation_window_token"
                ) from exc
            if token_event != event_id:
                raise ReservationError(
                    "Reservation window token is for a different event",
                    field="reservation_window_token",
                )

        async with redlock(
            f"event:{event_id}:reserve:{user_id}", redis_url=settings.redis_url, ttl_seconds=10
        ):
            event_ctx = await self._event_ctx_repo.get_by_event_id(event_id)
            if event_ctx is None:
                raise ReservationError("Event not found.", field="event_id")
            if event_ctx.status != "published":
                raise ReservationError("Event not on sale.", field="status")
            if total_quantity > event_ctx.max_tickets_per_user:
                raise ReservationError(
                    "Quantity exceeds the per-user maximum for this event", field="quantity"
                )
            now = _now()
            if event_ctx.sale_starts_at is None or event_ctx.sale_ends_at is None:
                raise ReservationError("Sale window not configured.", field="sale_window")
            if now < event_ctx.sale_starts_at or now > event_ctx.sale_ends_at:
                raise ReservationError("Sale window closed.", field="sale_window")
            if reservation_window_token is None and event_ctx.queue_required:
                raise ReservationError(
                    "Reservation window token is required for this event",
                    field="reservation_window_token",
                )
            held = await self._repo.active_quantity_for_user(user_id, event_id)
            if held + total_quantity > event_ctx.max_tickets_per_user:
                raise ReservationError("Ticket limit exceeded.", field="quantity")

            # every tier is locked and checked before any of them is drawn down
            inventories: list[tuple[TicketTypeInventory, int]] = []
            for ticket_type_id, quantity in sorted(items):
                inventory = await self._lock_inventory_nowait(ticket_type_id)
                if inventory is None or inventory.event_id != event_id:
                    raise ReservationError("Ticket type not found.", field="ticket_type_id")
                if inventory.reserved_count + quantity > inventory.capacity:
                    raise ReservationError("Capacity exhausted.", field="quantity")
                inventories.append((inventory, quantity))

            expires_at = now + timedelta(seconds=settings.reservation_ttl_seconds)
            reservation = Reservation(
                user_id=user_id,
                event_id=event_id,
                quantity=total_quantity,
                status=ReservationStatus.reserved,
                expires_at=expires_at,
                risk_score=evaluation.score,
                requires_review=evaluation.decision == FraudDecision.review,
            )
            reservation = await self._repo.insert(reservation)
            created_items = [
                ReservationItem(
                    reservation_id=reservation.id,
                    ticket_type_id=ticket_type_id,
                    quantity=quantity,
                )
                for ticket_type_id, quantity in sorted(items)
            ]
            self._session.add_all(created_items)
            for inventory, quantity in inventories:
                inventory.reserved_count = inventory.reserved_count + quantity
            await self._session.flush()
            await self._record(
                _RESERVATION_CREATED,
                actor_id=user_id,
                reservation_id=reservation.id,
                payload={
                    "event_id": str(event_id),
                    "items": [
                        {"ticket_type_id": str(tier), "quantity": qty}
                        for tier, qty in sorted(items)
                    ],
                    "quantity": total_quantity,
                },
            )
            await self._session.commit()

        if evaluation.decision == FraudDecision.review:
            await self._record_flagged(
                actor_id=user_id,
                reservation_id=reservation.id,
                payload=evaluation.to_payload(),
            )

        await _publish_reservation_created(reservation, created_items)
        return reservation, created_items

    # cancels an open reservation and releases its inventory
    @traced("reservation.cancel")
    async def cancel(
        self, *, actor_id: uuid.UUID, reservation_id: uuid.UUID
    ) -> tuple[Reservation, list[ReservationItem]]:
        reservation = await self._repo.get_by_id(reservation_id)
        if reservation is None or reservation.user_id != actor_id:
            raise ReservationError("Reservation not found.", field="reservation_id")
        if reservation.status in {ReservationStatus.cancelled, ReservationStatus.expired}:
            return reservation, await self._repo.list_items(reservation_id)
        if reservation.status == ReservationStatus.paid:
            raise ReservationError(
                "Paid reservations must be refunded, not cancelled", field="status"
            )
        async with redlock(
            f"reservation:{reservation_id}:lifecycle", redis_url=settings.redis_url, ttl_seconds=10
        ):
            items = await self._repo.list_items(reservation_id)
            for item in items:
                inventory = await self._lock_inventory_nowait(item.ticket_type_id)
                if inventory is None:
                    raise ReservationError("Ticket type not found.", field="ticket_type_id")
                inventory.reserved_count = max(0, inventory.reserved_count - item.quantity)
            reservation.status = ReservationStatus.cancelled
            await self._session.flush()
            await self._record(
                _RESERVATION_CANCELLED,
                actor_id=actor_id,
                reservation_id=reservation.id,
                payload={"event_id": str(reservation.event_id)},
            )
            await self._session.commit()
        await _publish_reservation_cancelled(reservation, items)
        return reservation, items

    # reads a reservation owned by the caller
    async def get_for_user(
        self, *, actor_id: uuid.UUID, reservation_id: uuid.UUID
    ) -> tuple[Reservation, list[ReservationItem]]:
        reservation = await self._repo.get_by_id(reservation_id)
        if reservation is None or reservation.user_id != actor_id:
            raise ReservationError("Reservation not found.", field="reservation_id")
        return reservation, await self._repo.list_items(reservation_id)

    # records that a reservation was blocked for fraud risk
    async def _record_blocked(
        self, *, actor_id: uuid.UUID, event_id: uuid.UUID, payload: dict[str, Any]
    ) -> None:
        try:
            await self._audit.record(
                action="RESERVATION_BLOCKED",
                actor_id=actor_id,
                entity_type="event",
                entity_id=str(event_id),
                payload=payload,
            )
        except Exception as exc:
            await logger.awarning(
                "audit_write_failed", action="RESERVATION_BLOCKED", error=repr(exc)
            )

    # records that a reservation was flagged for review
    async def _record_flagged(
        self, *, actor_id: uuid.UUID, reservation_id: uuid.UUID, payload: dict[str, Any]
    ) -> None:
        try:
            await self._audit.record(
                action="RESERVATION_FLAGGED",
                actor_id=actor_id,
                entity_type="reservation",
                entity_id=str(reservation_id),
                payload=payload,
            )
        except Exception as exc:
            await logger.awarning(
                "audit_write_failed", action="RESERVATION_FLAGGED", error=repr(exc)
            )

    # records an audit event without letting a failure interrupt the caller
    async def _record(
        self,
        action: str,
        *,
        actor_id: uuid.UUID,
        reservation_id: uuid.UUID,
        payload: dict[str, Any],
    ) -> None:
        try:
            await self._audit.record(
                action=action,
                actor_id=actor_id,
                entity_type="reservation",
                entity_id=str(reservation_id),
                payload=payload,
            )
        except Exception as exc:
            await logger.awarning("audit_write_failed", action=action, error=repr(exc))


# renders a reservation's tiers for a message payload
def _items_payload(items: list[ReservationItem]) -> list[dict[str, Any]]:
    return [
        {"ticket_type_id": str(item.ticket_type_id), "quantity": item.quantity} for item in items
    ]


# publishes that a reservation was created onto the shared nats connection
async def _publish_reservation_created(
    reservation: Reservation, items: list[ReservationItem]
) -> None:
    try:
        from messaging.publisher import publish as nats_publish  # type: ignore[import-untyped]
        from contracts.messaging.envelope import EventEnvelope  # type: ignore[import-untyped]

        envelope = EventEnvelope(
            occurred_at=datetime.now(UTC),
            aggregate_type="reservation",
            aggregate_id=str(reservation.id),
            actor_id=str(reservation.user_id),
            data={
                "reservation_id": str(reservation.id),
                "user_id": str(reservation.user_id),
                "event_id": str(reservation.event_id),
                "items": _items_payload(items),
                "quantity": reservation.quantity,
                "expires_at": reservation.expires_at.isoformat(),
            },
        )
        await asyncio.wait_for(
            nats_publish("sales.reservation.created.v1", envelope),
            timeout=_NATS_PUBLISH_TIMEOUT,
        )
    except Exception as exc:
        await logger.awarning(
            "nats_publish_failed",
            subject="sales.reservation.created.v1",
            error=repr(exc),
        )


# publishes that a reservation was cancelled onto the shared nats connection
async def _publish_reservation_cancelled(
    reservation: Reservation, items: list[ReservationItem]
) -> None:
    try:
        from messaging.publisher import publish as nats_publish  # type: ignore[import-untyped]
        from contracts.messaging.envelope import EventEnvelope  # type: ignore[import-untyped]

        envelope = EventEnvelope(
            occurred_at=datetime.now(UTC),
            aggregate_type="reservation",
            aggregate_id=str(reservation.id),
            actor_id=str(reservation.user_id),
            data={
                "reservation_id": str(reservation.id),
                "user_id": str(reservation.user_id),
                "event_id": str(reservation.event_id),
                "items": _items_payload(items),
                "quantity": reservation.quantity,
            },
        )
        await asyncio.wait_for(
            nats_publish("sales.reservation.cancelled.v1", envelope),
            timeout=_NATS_PUBLISH_TIMEOUT,
        )
    except Exception as exc:
        await logger.awarning(
            "nats_publish_failed",
            subject="sales.reservation.cancelled.v1",
            error=repr(exc),
        )
