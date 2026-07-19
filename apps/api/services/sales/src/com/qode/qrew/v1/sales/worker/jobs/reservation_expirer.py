import asyncio
from datetime import UTC, datetime

import structlog
from sqlalchemy import text

from com.qode.qrew.v1.sales.core.database import AsyncSessionLocal
from com.qode.qrew.v1.sales.core.config import settings

logger = structlog.get_logger(__name__)

_NATS_PUBLISH_TIMEOUT = 5.0

_SELECT_EXPIRED = text(
    """
    SELECT id, user_id, event_id, ticket_type_id, quantity
    FROM sales.reservations
    WHERE status = 'reserved' AND expires_at < now()
    ORDER BY expires_at
    LIMIT :batch
    FOR UPDATE SKIP LOCKED
    """
)

_EXPIRE_RESERVATION = text(
    "UPDATE sales.reservations SET status = 'expired', updated_at = now() WHERE id = :id"
)

_DECREMENT_INVENTORY = text(
    "UPDATE sales.ticket_type_inventory "
    "SET reserved_count = GREATEST(reserved_count - :qty, 0), updated_at = now() "
    "WHERE ticket_type_id = :tier_id"
)


async def sweep_expired() -> int:
    """Marks timed-out reservations as expired, releases inventory, and publishes expiry events."""
    swept = 0
    expired_rows: list[dict] = []

    async with AsyncSessionLocal() as session, session.begin():
        result = await session.execute(
            _SELECT_EXPIRED,
            {"batch": settings.reservation_sweep_batch_size},
        )
        rows = list(result.mappings())
        for row in rows:
            await session.execute(
                _DECREMENT_INVENTORY,
                {"tier_id": row["ticket_type_id"], "qty": row["quantity"]},
            )
            await session.execute(_EXPIRE_RESERVATION, {"id": row["id"]})
            expired_rows.append(dict(row))
            swept += 1

    for row in expired_rows:
        await _publish_expired(row)

    await logger.ainfo("reservations.sweep_expired", swept=swept)
    return swept


async def _publish_expired(row: dict) -> None:
    try:
        from messaging.publisher import publish as nats_publish  # type: ignore[import-untyped]
        from contracts.messaging.envelope import EventEnvelope  # type: ignore[import-untyped]

        envelope = EventEnvelope(
            occurred_at=datetime.now(UTC),
            aggregate_type="reservation",
            aggregate_id=str(row["id"]),
            actor_id=str(row["user_id"]),
            data={
                "reservation_id": str(row["id"]),
                "user_id": str(row["user_id"]),
                "event_id": str(row["event_id"]),
                "ticket_type_id": str(row["ticket_type_id"]),
                "quantity": row["quantity"],
            },
        )
        await asyncio.wait_for(
            nats_publish("sales.reservation.expired.v1", envelope),
            timeout=_NATS_PUBLISH_TIMEOUT,
        )
    except Exception as exc:
        await logger.awarning(
            "nats_publish_failed",
            subject="sales.reservation.expired.v1",
            reservation_id=str(row["id"]),
            error=repr(exc),
        )
