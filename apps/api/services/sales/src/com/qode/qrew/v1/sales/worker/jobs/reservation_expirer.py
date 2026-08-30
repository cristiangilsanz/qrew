# expires overdue reservations and releases the inventory they held
import asyncio
from datetime import UTC, datetime
from typing import Any

import structlog
from jobs import job, parse_crontab
from sqlalchemy import text

from com.qode.qrew.v1.sales.core.database import AsyncSessionLocal
from com.qode.qrew.v1.sales.core.config import settings

logger = structlog.get_logger(__name__)

_NATS_PUBLISH_TIMEOUT = 5.0

_SELECT_EXPIRED = text(
    """
    SELECT id, user_id, event_id, quantity
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

_SELECT_ITEMS = text(
    "SELECT ticket_type_id, quantity FROM sales.reservation_items "
    "WHERE reservation_id = :reservation_id"
)

_DECREMENT_INVENTORY = text(
    "UPDATE sales.ticket_type_inventory "
    "SET reserved_count = GREATEST(reserved_count - :qty, 0), updated_at = now() "
    "WHERE ticket_type_id = :tier_id"
)


# expires a batch of overdue reservations and releases their inventory
async def sweep_expired() -> int:
    swept = 0
    expired_rows: list[dict[str, Any]] = []

    async with AsyncSessionLocal() as session, session.begin():
        result = await session.execute(
            _SELECT_EXPIRED,
            {"batch": settings.reservation_sweep_batch_size},
        )
        rows = list(result.mappings())
        for row in rows:
            items = list(
                (await session.execute(_SELECT_ITEMS, {"reservation_id": row["id"]})).mappings()
            )
            for item in items:
                await session.execute(
                    _DECREMENT_INVENTORY,
                    {"tier_id": item["ticket_type_id"], "qty": item["quantity"]},
                )
            await session.execute(_EXPIRE_RESERVATION, {"id": row["id"]})
            expired_rows.append({**dict(row), "items": [dict(item) for item in items]})
            swept += 1

    for row in expired_rows:
        await _publish_expired(row)

    await logger.ainfo("reservations.sweep_expired", swept=swept)
    return swept


# publishes that a reservation expired onto the shared nats connection
async def _publish_expired(row: dict[str, Any]) -> None:
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
                "items": [
                    {
                        "ticket_type_id": str(item["ticket_type_id"]),
                        "quantity": item["quantity"],
                    }
                    for item in row["items"]
                ],
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


# expires overdue reservations and releases the inventory they held on a periodic schedule
@job("reservations.sweep_expired", cron=parse_crontab("* * * * *"), max_attempts=1)
async def run_sweep_expired(ctx: dict[str, Any]) -> None:
    del ctx
    await sweep_expired()
