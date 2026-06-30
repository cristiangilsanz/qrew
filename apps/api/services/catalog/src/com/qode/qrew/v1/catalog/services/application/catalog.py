import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.catalog.models.event import Event, EventStatus
from com.qode.qrew.v1.catalog.models.organisation import Organisation
from com.qode.qrew.v1.catalog.models.ticket_type import TicketType
from com.qode.qrew.v1.catalog.models.venue import Venue
from com.qode.qrew.v1.catalog.repositories.events.event import EventRepository
from com.qode.qrew.v1.catalog.repositories.organisation import OrganisationRepository
from com.qode.qrew.v1.catalog.repositories.ticket_type import TicketTypeRepository
from com.qode.qrew.v1.catalog.repositories.venue import VenueRepository


class PublicCatalogService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._event_repo = EventRepository(session)
        self._org_repo = OrganisationRepository(session)
        self._venue_repo = VenueRepository(session)
        self._ticket_type_repo = TicketTypeRepository(session)

    async def get_published_event(
        self, event_id: uuid.UUID
    ) -> tuple[Event, Organisation, Venue] | None:
        event = await self._event_repo.get_by_id(event_id)
        if event is None or event.status != EventStatus.published:
            return None
        org = await self._org_repo.get_by_id(event.organisation_id)
        venue = await self._venue_repo.get_by_id(event.venue_id)
        if org is None or venue is None:
            return None
        return event, org, venue

    async def get_ticket_types(self, event_id: uuid.UUID) -> list[TicketType]:
        stmt = self._ticket_type_repo.list_for_event_query(event_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_published_event_availability(
        self, event_id: uuid.UUID
    ) -> tuple[Event, list[TicketType]] | None:
        event = await self._event_repo.get_by_id(event_id)
        if event is None or event.status != EventStatus.published:
            return None
        tiers = await self.get_ticket_types(event_id)
        return event, tiers
