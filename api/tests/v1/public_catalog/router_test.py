import uuid
from collections.abc import AsyncGenerator, Sequence
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock

import pytest_asyncio
from httpx import AsyncClient

from com.qode.qrew.v1.service.core.infra.database import get_db
from com.qode.qrew.v1.service.main import app
from com.qode.qrew.v1.service.models.event import Event, EventStatus
from com.qode.qrew.v1.service.models.organisation import Organisation
from com.qode.qrew.v1.service.models.ticket_type import TicketType
from com.qode.qrew.v1.service.models.venue import Venue


def _event(status: EventStatus = EventStatus.published, **overrides: Any) -> Event:
    now = datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc)
    base: dict[str, Any] = {
        "id": uuid.uuid4(),
        "organisation_id": uuid.uuid4(),
        "venue_id": uuid.uuid4(),
        "name": "Concert",
        "description": "Live show",
        "starts_at": now + timedelta(days=10),
        "ends_at": now + timedelta(days=10, hours=4),
        "sale_starts_at": now,
        "sale_ends_at": now + timedelta(days=5),
        "max_tickets_per_user": 4,
        "status": status,
        "organiser_name": "Live Nation",
        "venue_city": "London",
        "published_at": now,
        "cancelled_at": None,
    }
    base.update(overrides)
    event = Event(**base)
    event.created_at = now
    event.updated_at = now
    return event


def _org(**overrides: Any) -> Organisation:
    base: dict[str, Any] = {
        "id": uuid.uuid4(),
        "slug": "live-nation",
        "name": "Live Nation",
        "description": "Promoter",
    }
    base.update(overrides)
    org = Organisation(**base)
    org.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return org


def _venue(**overrides: Any) -> Venue:
    base: dict[str, Any] = {
        "id": uuid.uuid4(),
        "name": "Wembley",
        "address_line": "Olympic Way",
        "city": "London",
        "country": "GB",
        "latitude": Decimal("51.555973"),
        "longitude": Decimal("-0.279672"),
        "geofence_radius_m": 300,
        "timezone": "Europe/London",
        "description": None,
    }
    base.update(overrides)
    venue = Venue(**base)
    venue.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return venue


def _tier(**overrides: Any) -> TicketType:
    base: dict[str, Any] = {
        "id": uuid.uuid4(),
        "event_id": uuid.uuid4(),
        "name": "general",
        "description": None,
        "capacity": 100,
        "reserved_count": 25,
        "price_cents": 5000,
        "currency": "EUR",
        "position": 0,
    }
    base.update(overrides)
    tier = TicketType(**base)
    tier.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return tier


def _install_db(
    event: Event | None,
    org: Organisation | None,
    venue: Venue | None,
    tiers: Sequence[TicketType],
) -> None:
    """Override get_db with a session whose repository lookups return the fixtures."""

    class _Session:
        async def execute(self, *_args: Any, **_kwargs: Any) -> Any:
            scalars = MagicMock()
            scalars.scalar_one_or_none = MagicMock()
            target = self._scalar_one_or_none()
            scalars.scalar_one_or_none.return_value = target
            result = MagicMock()
            result.scalar_one_or_none.return_value = target
            scalars_obj = MagicMock()
            scalars_obj.all.return_value = list(tiers)
            result.scalars.return_value = scalars_obj
            return result

        def _scalar_one_or_none(self) -> Any:
            return None

    session = _Session()
    # Repositories use select(...).where(...) which we can't introspect cheaply,
    # so we patch the repository methods instead.
    from com.qode.qrew.v1.service.repositories.event.event import EventRepository
    from com.qode.qrew.v1.service.repositories.organisation.organisation import (
        OrganisationRepository,
    )
    from com.qode.qrew.v1.service.repositories.venue.venue import VenueRepository

    async def _evt_get(self: Any, _id: uuid.UUID) -> Event | None:
        del self
        return event

    async def _org_get(self: Any, _id: uuid.UUID) -> Organisation | None:
        del self
        return org

    async def _venue_get(self: Any, _id: uuid.UUID) -> Venue | None:
        del self
        return venue

    EventRepository.get_by_id = _evt_get  # type: ignore[method-assign]
    OrganisationRepository.get_by_id = _org_get  # type: ignore[method-assign]
    VenueRepository.get_by_id = _venue_get  # type: ignore[method-assign]

    async def _db() -> AsyncGenerator[Any, None]:
        yield session

    app.dependency_overrides[get_db] = _db


@pytest_asyncio.fixture
async def _cleanup_overrides() -> AsyncGenerator[None, None]:  # pyright: ignore[reportUnusedFunction]
    yield
    app.dependency_overrides.pop(get_db, None)


async def test_get_public_event_returns_404_for_draft(
    client: AsyncClient, _cleanup_overrides: None
) -> None:
    del _cleanup_overrides
    event = _event(status=EventStatus.draft)
    _install_db(event, _org(), _venue(), [])
    response = await client.get(f"/v1/events/{event.id}")
    assert response.status_code == 404


async def test_get_public_event_returns_404_for_cancelled(
    client: AsyncClient, _cleanup_overrides: None
) -> None:
    del _cleanup_overrides
    event = _event(status=EventStatus.cancelled)
    _install_db(event, _org(), _venue(), [])
    response = await client.get(f"/v1/events/{event.id}")
    assert response.status_code == 404


async def test_get_public_event_returns_payload_for_published(
    client: AsyncClient, _cleanup_overrides: None
) -> None:
    del _cleanup_overrides
    event = _event()
    tier = _tier(event_id=event.id, capacity=100, reserved_count=25)
    _install_db(
        event, _org(id=event.organisation_id), _venue(id=event.venue_id), [tier]
    )
    response = await client.get(f"/v1/events/{event.id}")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Concert"
    assert body["venue"]["geofence_radius_m"] == 300
    assert body["ticket_types"][0]["available"] == 75


async def test_event_availability_returns_only_projection(
    client: AsyncClient, _cleanup_overrides: None
) -> None:
    del _cleanup_overrides
    event = _event()
    tier = _tier(event_id=event.id, capacity=100, reserved_count=40)
    _install_db(
        event, _org(id=event.organisation_id), _venue(id=event.venue_id), [tier]
    )
    response = await client.get(f"/v1/events/{event.id}/availability")
    assert response.status_code == 200
    body = response.json()
    assert body["ticket_types"] == [
        {
            "id": str(tier.id),
            "name": tier.name,
            "available": 60,
            "price_cents": tier.price_cents,
            "currency": tier.currency,
        }
    ]


async def test_event_availability_404_for_unpublished(
    client: AsyncClient, _cleanup_overrides: None
) -> None:
    del _cleanup_overrides
    event = _event(status=EventStatus.draft)
    _install_db(event, _org(), _venue(), [])
    response = await client.get(f"/v1/events/{event.id}/availability")
    assert response.status_code == 404
