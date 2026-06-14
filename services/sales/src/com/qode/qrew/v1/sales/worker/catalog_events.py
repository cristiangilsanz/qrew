"""Sales NATS worker: updates EventContext and TicketTypeInventory projections from catalog events."""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any

import structlog

from com.qode.qrew.v1.sales.core.infra.database import AsyncSessionLocal
from com.qode.qrew.v1.sales.repositories.projections import (
    EventContextRepository,
    TicketTypeInventoryRepository,
)

logger = structlog.get_logger(__name__)

STREAM = "CATALOG"
DURABLE = "sales-catalog-handler"


async def _parse(raw: bytes) -> dict[str, Any] | None:
    try:
        data = json.loads(raw.decode())
        assert isinstance(data, dict)
        return data  # type: ignore[return-value]
    except Exception:
        await logger.awarning("catalog_events.parse_error")
        return None


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).astimezone(timezone.utc)
    except Exception:
        return None


async def _upsert_event_ctx(
    data: dict[str, Any],
    *,
    status: str,
) -> None:
    try:
        event_id = uuid.UUID(str(data["data"]["event_id"]))
    except (KeyError, ValueError):
        await logger.awarning("catalog_events.upsert_event_ctx.bad_payload")
        return
    d = data["data"]
    sale_starts_at = _parse_dt(d.get("sale_starts_at"))
    sale_ends_at = _parse_dt(d.get("sale_ends_at"))
    max_tickets_per_user = int(d.get("max_tickets_per_user", 10))
    queue_required = bool(d.get("queue_required", False))
    queue_admit_rate = int(d.get("queue_admit_rate_per_minute", 50))
    async with AsyncSessionLocal() as session:
        await EventContextRepository(session).upsert(
            event_id=event_id,
            status=status,
            sale_starts_at=sale_starts_at,
            sale_ends_at=sale_ends_at,
            max_tickets_per_user=max_tickets_per_user,
            queue_required=queue_required,
            queue_admit_rate_per_minute=queue_admit_rate,
        )
        await session.commit()
    await logger.ainfo("catalog_events.event_upserted", event_id=str(event_id), status=status)


async def handle_event_published(raw: bytes) -> None:
    data = await _parse(raw)
    if data is None:
        return
    await _upsert_event_ctx(data, status="published")


async def handle_event_cancelled(raw: bytes) -> None:
    data = await _parse(raw)
    if data is None:
        return
    await _upsert_event_ctx(data, status="cancelled")


async def handle_event_draft(raw: bytes) -> None:
    data = await _parse(raw)
    if data is None:
        return
    await _upsert_event_ctx(data, status="draft")


async def handle_ticket_type_created(raw: bytes) -> None:
    data = await _parse(raw)
    if data is None:
        return
    try:
        ticket_type_id = uuid.UUID(str(data["data"]["ticket_type_id"]))
        event_id = uuid.UUID(str(data["data"]["event_id"]))
        capacity = int(data["data"]["capacity"])
        price_cents = int(data["data"].get("price_cents", 0))
        currency = str(data["data"].get("currency", "EUR"))
    except (KeyError, ValueError):
        await logger.awarning("catalog_events.ticket_type_created.bad_payload")
        return
    async with AsyncSessionLocal() as session:
        await TicketTypeInventoryRepository(session).upsert(
            ticket_type_id=ticket_type_id,
            event_id=event_id,
            capacity=capacity,
            price_cents=price_cents,
            currency=currency,
        )
        await session.commit()
    await logger.ainfo(
        "catalog_events.ticket_type_upserted", ticket_type_id=str(ticket_type_id)
    )


async def handle_ticket_type_updated(raw: bytes) -> None:
    await handle_ticket_type_created(raw)


_HANDLERS = {
    "catalog.event.published.v1": handle_event_published,
    "catalog.event.cancelled.v1": handle_event_cancelled,
    "catalog.event.draft.v1": handle_event_draft,
    "catalog.ticket_type.created.v1": handle_ticket_type_created,
    "catalog.ticket_type.updated.v1": handle_ticket_type_updated,
}


async def run_catalog_event_subscriber(nats_url: str) -> None:
    import nats
    from nats.js.api import ConsumerConfig, DeliverPolicy

    nc = await nats.connect(nats_url)  # type: ignore[reportUnknownMemberType]
    js = nc.jetstream()  # type: ignore[reportUnknownMemberType]

    try:
        await js.find_stream_name_by_subject("catalog.>")
    except Exception:
        await js.add_stream(name=STREAM, subjects=["catalog.>"])  # type: ignore[misc]

    for subject, handler in _HANDLERS.items():
        durable = f"{DURABLE}-{subject.replace('.', '-')}"
        config = ConsumerConfig(
            durable_name=durable,
            deliver_policy=DeliverPolicy.ALL,
            filter_subject=subject,
        )
        psub = await js.subscribe(
            subject, durable=durable, config=config, stream=STREAM
        )  # type: ignore[misc]
        await logger.ainfo("catalog_events.subscribed", subject=subject)

        async def _consume(psub: Any = psub, h: Any = handler) -> None:
            async for msg in psub.messages:  # type: ignore[attr-defined]
                try:
                    await h(msg.data)  # type: ignore[attr-defined]
                    await msg.ack()  # type: ignore[attr-defined]
                except Exception:
                    await logger.awarning("catalog_events.handler_error")
                    await msg.nak()  # type: ignore[attr-defined]

        asyncio.create_task(_consume())

    await logger.ainfo("catalog_events.all_subscribed")
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass
    finally:
        await nc.drain()
