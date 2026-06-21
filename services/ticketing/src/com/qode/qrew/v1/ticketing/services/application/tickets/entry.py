import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.ticketing.core.config import settings
from com.qode.qrew.v1.ticketing.models.ticket import TicketState
from com.qode.qrew.v1.ticketing.services.domain.tickets.lifecycle import (
    TicketBusyError,
    TicketNotFoundError,
    TicketTransitionError,
    transition_ticket,
)
from locking import LockUnavailableError, redlock

__all__ = [
    "TicketBusyError",
    "TicketNotFoundError",
    "TicketTransitionError",
    "LockUnavailableError",
    "use_ticket",
]


async def use_ticket(
    session: AsyncSession,
    *,
    ticket_id: uuid.UUID,
    actor_id: uuid.UUID,
) -> None:
    async with redlock(f"ticket:{ticket_id}:entry", redis_url=settings.redis_url, ttl_seconds=10):
        try:
            await transition_ticket(
                session,
                ticket_id=ticket_id,
                to_state=TicketState.used,
                reason="entry_validated",
                actor_id=actor_id,
            )
        except TicketTransitionError as exc:
            if "terminal" in exc.message.lower() or "used" in exc.message.lower():
                return
            raise
        await session.commit()
