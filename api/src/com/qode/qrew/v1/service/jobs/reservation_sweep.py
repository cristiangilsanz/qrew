from typing import Any

import structlog
from sqlalchemy import text

from com.qode.qrew.v1.service.core.infra.database import AsyncSessionLocal
from com.qode.qrew.v1.service.core.jobs import job
from com.qode.qrew.v1.service.settings import settings

logger = structlog.get_logger(__name__)

_SELECT_EXPIRED = text(
    """
    SELECT id, ticket_type_id, quantity
    FROM reservations
    WHERE status = 'reserved' AND expires_at < now()
    ORDER BY expires_at
    LIMIT :batch
    FOR UPDATE SKIP LOCKED
    """
)

_EXPIRE_RESERVATION = text(
    "UPDATE reservations SET status = 'expired', updated_at = now() WHERE id = :id"
)

_CANCEL_TICKETS = text(
    "UPDATE tickets SET state = 'cancelled', updated_at = now() "
    "WHERE reservation_id = :id AND state = 'reserved'"
)

_DECREMENT_TIER = text(
    "UPDATE ticket_types SET reserved_count = GREATEST(reserved_count - :qty, 0), "
    "updated_at = now() WHERE id = :tier_id"
)


@job(name="reservations.sweep_expired", cron="* * * * *", max_attempts=1)
async def sweep_expired(ctx: dict[str, Any]) -> dict[str, Any]:
    """Mark expired reservations and free their reserved capacity."""
    del ctx
    swept = 0
    async with AsyncSessionLocal() as session, session.begin():
        result = await session.execute(
            _SELECT_EXPIRED,
            {"batch": settings.reservation_sweep_batch_size},
        )
        rows = list(result.mappings())
        for row in rows:
            await session.execute(_CANCEL_TICKETS, {"id": row["id"]})
            await session.execute(
                _DECREMENT_TIER,
                {"tier_id": row["ticket_type_id"], "qty": row["quantity"]},
            )
            await session.execute(_EXPIRE_RESERVATION, {"id": row["id"]})
            swept += 1
    await logger.ainfo("reservations.sweep_expired", swept=swept)
    return {"swept": swept}
