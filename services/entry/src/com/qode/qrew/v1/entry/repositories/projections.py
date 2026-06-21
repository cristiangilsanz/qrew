import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.entry.models.projections import (
    Event,
    OrganisationMember,
    TicketContext,
    User,
)


class EventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, event_id: uuid.UUID) -> Event | None:
        result = await self._session.execute(
            select(Event).where(Event.id == event_id).limit(1)
        )
        return result.scalar_one_or_none()


class OrganisationMemberRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(
        self, organisation_id: uuid.UUID, user_id: uuid.UUID
    ) -> OrganisationMember | None:
        result = await self._session.execute(
            select(OrganisationMember)
            .where(
                OrganisationMember.organisation_id == organisation_id,
                OrganisationMember.user_id == user_id,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self._session.execute(
            select(User).where(User.id == user_id).limit(1)
        )
        return result.scalar_one_or_none()


class TicketContextRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, ticket_id: uuid.UUID) -> TicketContext | None:
        result = await self._session.execute(
            select(TicketContext).where(TicketContext.ticket_id == ticket_id).limit(1)
        )
        return result.scalar_one_or_none()

    async def upsert(
        self,
        ticket_id: uuid.UUID,
        event_id: uuid.UUID,
        state: str,
        *,
        venue_id: uuid.UUID | None = None,
        owner_user_id: uuid.UUID | None = None,
        bound_device_id: uuid.UUID | None = None,
    ) -> None:
        stmt = (
            pg_insert(TicketContext)
            .values(
                ticket_id=ticket_id,
                event_id=event_id,
                state=state,
                venue_id=venue_id,
                owner_user_id=owner_user_id,
                bound_device_id=bound_device_id,
                updated_at=datetime.now(UTC),
            )
            .on_conflict_do_update(
                index_elements=["ticket_id"],
                set_={
                    "state": state,
                    "venue_id": venue_id,
                    "owner_user_id": owner_user_id,
                    "bound_device_id": bound_device_id,
                    "updated_at": datetime.now(UTC),
                },
            )
        )
        await self._session.execute(stmt)
        await self._session.flush()
