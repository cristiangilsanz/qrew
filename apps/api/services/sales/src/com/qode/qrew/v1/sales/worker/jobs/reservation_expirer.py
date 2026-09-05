# expires overdue reservations and releases the inventory they held
from typing import Any

import structlog
from jobs import job, parse_crontab
from sqlalchemy import text

from sqlalchemy.ext.asyncio import AsyncSession

from outbox import record as record_event

from com.qode.qrew.v1.sales.models.outbox import EventOutbox
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
            await _publish_expired(session, row)

    await logger.ainfo("reservations.sweep_expired", swept=swept)
    return swept


# publishes that a reservation expired onto the shared nats connection
async def _publish_expired(session: AsyncSession, row: dict[str, Any]) -> None:
    await record_event(
        session,
        EventOutbox,
        subject="sales.reservation.expired.v1",
        aggregate_type="reservation",
        aggregate_id=str(row["id"]),
        actor_id=str(row["user_id"]),
        data={
            "reservation_id": str(row["id"]),
            "user_id": str(row["user_id"]),
            "event_id": str(row["event_id"]),
            "items": [
                {"ticket_type_id": str(i["ticket_type_id"]), "quantity": i["quantity"]}
                for i in row.get("items", [])
            ],
            "quantity": row.get("quantity"),
        },
    )


# expires overdue reservations and releases the inventory they held on a periodic schedule
@job("reservations.sweep_expired", cron=parse_crontab("* * * * *"), max_attempts=1)
async def run_sweep_expired(ctx: dict[str, Any]) -> None:
    del ctx
    await sweep_expired()
