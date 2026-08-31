# tests catalog
import json
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from com.qode.qrew.v1.ticketing.worker.subscribers.catalog import (
    _upsert_geofence,
    handle_event_draft,
    handle_event_ongoing,
    handle_event_published,
)

_MODULE = "com.qode.qrew.v1.ticketing.worker.subscribers.catalog"


# handles repo
def _repo() -> MagicMock:
    repo = MagicMock()
    repo.upsert_venue = AsyncMock()
    return repo


# verifies that the geofence is stored when it travels with the event
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


# verifies that nothing is stored when the event carries no geofence
@pytest.mark.asyncio
async def test_nothing_is_stored_when_the_event_carries_no_geofence() -> None:
    repo = _repo()
    await _upsert_geofence(repo, {"data": {}}, event_id=uuid.uuid4(), venue_id=uuid.uuid4())
    repo.upsert_venue.assert_not_awaited()


# verifies that a malformed geofence is discarded
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


# builds the envelope a catalog event arrives in
def _envelope(**data: object) -> bytes:
    return json.dumps({"data": data}).encode()


# runs a handler against a session whose repository is a stand in
@asynccontextmanager
async def _patched_session(repo: MagicMock) -> AsyncIterator[MagicMock]:
    session = MagicMock()
    session.commit = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    with (
        patch(f"{_MODULE}.AsyncSessionLocal", return_value=session),
        patch(f"{_MODULE}.EventVenueContextRepository", return_value=repo),
    ):
        yield session


# verifies that a published event is projected with its window and its geofence
async def test_a_published_event_is_projected() -> None:
    repo = MagicMock()
    repo.upsert_event = AsyncMock()
    repo.upsert_venue = AsyncMock()
    event_id, venue_id = uuid.uuid4(), uuid.uuid4()
    raw = _envelope(
        event_id=str(event_id),
        venue_id=str(venue_id),
        starts_at="2026-06-01T20:00:00+00:00",
        ends_at="2026-06-01T23:00:00+00:00",
        latitude=40.0,
        longitude=-3.0,
        geofence_radius_m=500,
        timezone="Europe/Madrid",
    )
    async with _patched_session(repo) as session:
        await handle_event_published(raw)
    repo.upsert_event.assert_awaited_once()
    repo.upsert_venue.assert_awaited_once()
    session.commit.assert_awaited_once()


# verifies that an event without an identifier is discarded rather than projected
async def test_a_published_event_without_an_identifier_is_discarded() -> None:
    repo = MagicMock()
    repo.upsert_event = AsyncMock()
    async with _patched_session(repo):
        await handle_event_published(_envelope(venue_id=str(uuid.uuid4())))
    repo.upsert_event.assert_not_awaited()


# verifies that an ongoing event is projected with the status the gate reads
async def test_an_ongoing_event_updates_its_status() -> None:
    repo = MagicMock()
    repo.upsert_event = AsyncMock()
    async with _patched_session(repo) as session:
        await handle_event_ongoing(
            _envelope(event_id=str(uuid.uuid4()), venue_id=str(uuid.uuid4()))
        )
    assert repo.upsert_event.await_args.kwargs["event_status"] == "ongoing"
    session.commit.assert_awaited_once()


# verifies that an event returned to draft is projected with that status
async def test_a_draft_event_updates_its_status() -> None:
    repo = MagicMock()
    repo.upsert_event = AsyncMock()
    async with _patched_session(repo) as session:
        await handle_event_draft(_envelope(event_id=str(uuid.uuid4()), venue_id=str(uuid.uuid4())))
    assert repo.upsert_event.await_args.kwargs["event_status"] == "draft"
    session.commit.assert_awaited_once()


# verifies that a status change without an identifier is discarded
async def test_a_status_change_without_an_identifier_is_discarded() -> None:
    repo = MagicMock()
    repo.upsert_event = AsyncMock()
    async with _patched_session(repo):
        await handle_event_ongoing(_envelope())
    repo.upsert_event.assert_not_awaited()
