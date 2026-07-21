import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.ticketing.models.ticket import Ticket, TicketState


class TicketRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, ticket_id: uuid.UUID) -> Ticket | None:
        return await self._session.get(Ticket, ticket_id)

    async def list_by_reservation(self, reservation_id: uuid.UUID) -> list[Ticket]:
        result = await self._session.execute(
            select(Ticket).where(Ticket.reservation_id == reservation_id)
        )
        return list(result.scalars().all())

    async def list_by_user_device_state(
        self,
        user_id: uuid.UUID,
        device_id: uuid.UUID,
        state: TicketState,
    ) -> list[Ticket]:
        result = await self._session.execute(
            select(Ticket).where(
                Ticket.owner_user_id == user_id,
                Ticket.bound_device_id == device_id,
                Ticket.state == state,
            )
        )
        return list(result.scalars().all())

    async def list_by_user(self, user_id: uuid.UUID) -> list[Ticket]:
        result = await self._session.execute(
            select(Ticket).where(Ticket.owner_user_id == user_id).order_by(Ticket.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_active_by_event(self, event_id: uuid.UUID) -> list[Ticket]:
        """Return all non-terminal tickets for an event (issued, reserved, frozen, etc.)."""
        terminal = {TicketState.cancelled, TicketState.used, TicketState.expired}
        result = await self._session.execute(
            select(Ticket).where(
                Ticket.event_id == event_id,
                Ticket.state.not_in(terminal),
            )
        )
        return list(result.scalars().all())

    async def flush(self) -> None:
        await self._session.flush()
