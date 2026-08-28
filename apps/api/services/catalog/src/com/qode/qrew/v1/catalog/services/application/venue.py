# creates and reads venues including their geofence and timezone
import uuid
from decimal import Decimal
from zoneinfo import available_timezones

import structlog
from sqlalchemy import Select

from com.qode.qrew.v1.catalog.services.application.audit import AuditService
from com.qode.qrew.v1.catalog.core.errors import DomainError
from observability import traced
from com.qode.qrew.v1.catalog.models.venue import Venue
from com.qode.qrew.v1.catalog.repositories.venue import VenueRepository

logger = structlog.get_logger(__name__)

_GEOFENCE_MIN_M = 50
_GEOFENCE_MAX_M = 5000
_AVAILABLE_TIMEZONES = available_timezones()


class VenueError(DomainError):
    pass


# rejects coordinates outside the valid latitude and longitude range
def _validate_coordinates(latitude: Decimal, longitude: Decimal) -> None:
    if latitude < Decimal("-90") or latitude > Decimal("90"):
        raise VenueError("Latitude out of range", field="latitude")
    if longitude < Decimal("-180") or longitude > Decimal("180"):
        raise VenueError("Longitude out of range", field="longitude")


# rejects a geofence radius outside the allowed range
def _validate_radius(radius_m: int) -> None:
    if radius_m < _GEOFENCE_MIN_M or radius_m > _GEOFENCE_MAX_M:
        raise VenueError(
            "Geofence radius must be between 50 and 5000 metres",
            field="geofence_radius_m",
        )


# rejects a timezone that is not recognised
def _validate_timezone(timezone: str) -> None:
    if timezone not in _AVAILABLE_TIMEZONES:
        raise VenueError("Unknown timezone", field="timezone")


# rejects a country that is not a two letter code
def _validate_country(country: str) -> None:
    if len(country) != 2 or not country.isalpha():
        raise VenueError("Country must be an ISO-3166-1 alpha-2 code", field="country")


class VenueService:
    # stores the repository and audit service the venue service uses
    def __init__(self, repo: VenueRepository, audit: AuditService) -> None:
        self._repo = repo
        self._audit = audit

    # builds the query that lists venues filtered by city or country
    def list_query(
        self, city: str | None = None, country: str | None = None
    ) -> Select[tuple[Venue]]:
        return self._repo.list_query(city=city, country=country)

    # reads a venue by its identifier
    async def get_by_id(self, venue_id: uuid.UUID) -> Venue | None:
        return await self._repo.get_by_id(venue_id)

    # creates a venue after validating its location and geofence
    @traced("venue.create")
    async def create_venue(
        self,
        *,
        actor_id: uuid.UUID,
        name: str,
        address_line: str,
        city: str,
        country: str,
        latitude: Decimal,
        longitude: Decimal,
        geofence_radius_m: int,
        timezone: str,
        description: str | None,
    ) -> Venue:
        _validate_country(country)
        _validate_coordinates(latitude, longitude)
        _validate_radius(geofence_radius_m)
        _validate_timezone(timezone)
        venue = Venue(
            name=name,
            address_line=address_line,
            city=city,
            country=country.upper(),
            latitude=latitude,
            longitude=longitude,
            geofence_radius_m=geofence_radius_m,
            timezone=timezone,
            description=description,
        )
        venue = await self._repo.insert(venue)
        try:
            await self._audit.record(
                action="venue_created",
                actor_id=actor_id,
                entity_type="venue",
                entity_id=str(venue.id),
                payload={"name": venue.name, "city": venue.city, "country": venue.country},
            )
        except Exception as exc:
            await logger.awarning("audit_write_failed", action="venue_created", error=repr(exc))
        return venue
