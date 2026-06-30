import uuid

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.catalog.models.ticket_type import TicketType


class TicketTypeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, ticket_type_id: uuid.UUID) -> TicketType | None:
        result = await self._session.execute(
            select(TicketType).where(
                TicketType.id == ticket_type_id,
                TicketType.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_event_and_name(self, event_id: uuid.UUID, name: str) -> TicketType | None:
        result = await self._session.execute(
            select(TicketType).where(
                TicketType.event_id == event_id,
                TicketType.name == name,
                TicketType.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def insert(self, ticket_type: TicketType) -> TicketType:
        self._session.add(ticket_type)
        await self._session.flush()
        await self._session.refresh(ticket_type)
        return ticket_type

    async def flush(self) -> None:
        await self._session.flush()

    def list_for_event_query(self, event_id: uuid.UUID) -> Select[tuple[TicketType]]:
        return (
            select(TicketType)
            .where(TicketType.event_id == event_id, TicketType.deleted_at.is_(None))
            .order_by(TicketType.position, TicketType.created_at)
        )
