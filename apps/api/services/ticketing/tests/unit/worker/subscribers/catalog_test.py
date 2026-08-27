import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from com.qode.qrew.v1.ticketing.worker.subscribers.catalog import _upsert_geofence


def _repo() -> MagicMock:
    repo = MagicMock()
    repo.upsert_venue = AsyncMock()
    return repo


@pytest.mark.asyncio
async def test_the_geofence_is_stored_when_it_travels_with_the_event() -> None:
    repo = _repo()
    event_id, venue_id = uuid.uuid4(), uuid.uuid4()
    data = {
        "data": {
            "latitude": "40.416775",
            "longitude": "-3.703790",
            "geofence_radius_m": 150,
            "timezone": "Europe/Madrid",
        }
    }

    await _upsert_geofence(repo, data, event_id=event_id, venue_id=venue_id)

    repo.upsert_venue.assert_awaited_once_with(
        event_id=event_id,
        venue_id=venue_id,
        latitude=Decimal("40.416775"),
        longitude=Decimal("-3.703790"),
        geofence_radius_m=150,
        timezone="Europe/Madrid",
    )


@pytest.mark.asyncio
async def test_nothing_is_stored_when_the_event_carries_no_geofence() -> None:
    repo = _repo()
    await _upsert_geofence(repo, {"data": {}}, event_id=uuid.uuid4(), venue_id=uuid.uuid4())
    repo.upsert_venue.assert_not_awaited()


@pytest.mark.asyncio
async def test_a_malformed_geofence_is_discarded() -> None:
    repo = _repo()
    data = {
        "data": {
            "latitude": "north",
            "longitude": "-3.7",
            "geofence_radius_m": 1,
            "timezone": "UTC",
        }
    }
    await _upsert_geofence(repo, data, event_id=uuid.uuid4(), venue_id=uuid.uuid4())
    repo.upsert_venue.assert_not_awaited()
