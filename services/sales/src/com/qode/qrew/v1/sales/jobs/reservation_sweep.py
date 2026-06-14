import structlog
from sqlalchemy import text

from com.qode.qrew.v1.sales.core.infra.database import AsyncSessionLocal
from com.qode.qrew.v1.sales.settings import settings

logger = structlog.get_logger(__name__)

_SELECT_EXPIRED = text(
    """
    SELECT id, ticket_type_id, quantity
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
    """Mark expired reservations and free their reserved inventory. Returns count swept."""
    swept = 0
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
            swept += 1
    await logger.ainfo("reservations.sweep_expired", swept=swept)
    return swept
