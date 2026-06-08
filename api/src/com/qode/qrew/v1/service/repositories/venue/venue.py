import uuid

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.service.models.venue import Venue


class VenueRepository:
    """Data access for the venues table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, venue_id: uuid.UUID) -> Venue | None:
        result = await self._session.execute(
            select(Venue).where(Venue.id == venue_id, Venue.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def insert(self, venue: Venue) -> Venue:
        self._session.add(venue)
        await self._session.flush()
        await self._session.refresh(venue)
        return venue

    def list_query(
        self, city: str | None = None, country: str | None = None
    ) -> Select[tuple[Venue]]:
        """Build a filtered, soft-delete-aware query for the public list."""
        stmt = select(Venue).where(Venue.deleted_at.is_(None))
        if city is not None:
            stmt = stmt.where(Venue.city == city)
        if country is not None:
            stmt = stmt.where(Venue.country == country.upper())
        return stmt
