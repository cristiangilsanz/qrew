import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from com.qode.qrew.v1.service.models.venue import Venue
from com.qode.qrew.v1.service.services.venue import VenueError, VenueService


def _service() -> tuple[VenueService, MagicMock, MagicMock]:
    repo = MagicMock()

    async def _insert(venue: Venue) -> Venue:
        venue.id = uuid.uuid4()
        return venue

    repo.insert = AsyncMock(side_effect=_insert)
    audit = MagicMock()
    audit.record = AsyncMock()
    return VenueService(repo, audit), repo, audit


def _valid_kwargs() -> dict[str, object]:
    return {
        "actor_id": uuid.uuid4(),
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


async def test_create_venue_persists_and_audits() -> None:
    service, repo, audit = _service()
    venue = await service.create_venue(**_valid_kwargs())  # type: ignore[arg-type]
    assert venue.country == "GB"
    repo.insert.assert_awaited_once()
    audit.record.assert_awaited_once()


async def test_create_venue_rejects_bad_country() -> None:
    service, *_ = _service()
    kwargs = _valid_kwargs() | {"country": "GBR"}
    with pytest.raises(VenueError, match="ISO-3166"):
        await service.create_venue(**kwargs)  # type: ignore[arg-type]


async def test_create_venue_rejects_bad_latitude() -> None:
    service, *_ = _service()
    kwargs = _valid_kwargs() | {"latitude": Decimal("91")}
    with pytest.raises(VenueError, match="Latitude"):
        await service.create_venue(**kwargs)  # type: ignore[arg-type]


async def test_create_venue_rejects_bad_longitude() -> None:
    service, *_ = _service()
    kwargs = _valid_kwargs() | {"longitude": Decimal("-181")}
    with pytest.raises(VenueError, match="Longitude"):
        await service.create_venue(**kwargs)  # type: ignore[arg-type]


async def test_create_venue_rejects_bad_radius() -> None:
    service, *_ = _service()
    kwargs = _valid_kwargs() | {"geofence_radius_m": 10}
    with pytest.raises(VenueError, match="radius"):
        await service.create_venue(**kwargs)  # type: ignore[arg-type]


async def test_create_venue_rejects_unknown_timezone() -> None:
    service, *_ = _service()
    kwargs = _valid_kwargs() | {"timezone": "Mars/Olympus_Mons"}
    with pytest.raises(VenueError, match="timezone"):
        await service.create_venue(**kwargs)  # type: ignore[arg-type]


async def test_create_venue_normalises_country_to_upper() -> None:
    service, *_ = _service()
    kwargs = _valid_kwargs() | {"country": "gb"}
    venue = await service.create_venue(**kwargs)  # type: ignore[arg-type]
    assert venue.country == "GB"
