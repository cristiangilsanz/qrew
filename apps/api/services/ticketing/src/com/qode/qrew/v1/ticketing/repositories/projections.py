import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.ticketing.models.projections import DeviceContext, EventVenueContext


class EventVenueContextRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_event_id(self, event_id: uuid.UUID) -> EventVenueContext | None:
        return await self._session.get(EventVenueContext, event_id)

    async def upsert_event(
        self,
        *,
        event_id: uuid.UUID,
        venue_id: uuid.UUID,
        event_status: str,
        starts_at: datetime | None = None,
        ends_at: datetime | None = None,
    ) -> None:
        ctx = await self._session.get(EventVenueContext, event_id)
        if ctx is None:
            ctx = EventVenueContext(
                event_id=event_id,
                venue_id=venue_id,
                event_status=event_status,
                starts_at=starts_at,
                ends_at=ends_at,
            )
            self._session.add(ctx)
        else:
            ctx.event_status = event_status
            if venue_id != ctx.venue_id:
                ctx.venue_id = venue_id
            if starts_at is not None:
                ctx.starts_at = starts_at
            if ends_at is not None:
                ctx.ends_at = ends_at
        ctx.updated_at = datetime.now(UTC)
        await self._session.flush()

    async def upsert_venue(
        self,
        *,
        event_id: uuid.UUID,
        venue_id: uuid.UUID,
        latitude: Decimal,
        longitude: Decimal,
        geofence_radius_m: int,
        timezone: str,
    ) -> None:
        ctx = await self._session.get(EventVenueContext, event_id)
        if ctx is None:
            ctx = EventVenueContext(
                event_id=event_id,
                venue_id=venue_id,
                event_status="draft",
                latitude=latitude,
                longitude=longitude,
                geofence_radius_m=geofence_radius_m,
                timezone=timezone,
            )
            self._session.add(ctx)
        else:
            ctx.latitude = latitude
            ctx.longitude = longitude
            ctx.geofence_radius_m = geofence_radius_m
            ctx.timezone = timezone
        ctx.updated_at = datetime.now(UTC)
        await self._session.flush()


class DeviceContextRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_device_id(self, device_id: uuid.UUID) -> DeviceContext | None:
        return await self._session.get(DeviceContext, device_id)

    async def upsert(
        self,
        *,
        device_id: uuid.UUID,
        user_id: uuid.UUID,
        attested_at: datetime | None,
        revoked_at: datetime | None,
    ) -> None:
        ctx = await self._session.get(DeviceContext, device_id)
        if ctx is None:
            ctx = DeviceContext(
                device_id=device_id,
                user_id=user_id,
                attested_at=attested_at,
                revoked_at=revoked_at,
            )
            self._session.add(ctx)
        else:
            ctx.user_id = user_id
            ctx.attested_at = attested_at
            ctx.revoked_at = revoked_at
        ctx.updated_at = datetime.now(UTC)
        await self._session.flush()
