import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from com.qode.qrew.v1.service.models.event import Event, EventStatus
from com.qode.qrew.v1.service.services.event import EventError, EventService


def _times() -> dict[str, datetime]:
    now = datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc)
    return {
        "sale_starts_at": now,
        "sale_ends_at": now + timedelta(days=5),
        "starts_at": now + timedelta(days=10),
        "ends_at": now + timedelta(days=10, hours=4),
    }


_DEFAULT = object()


def _service(
    *,
    org: Any = _DEFAULT,
    venue: Any = _DEFAULT,
    existing_event: Event | None = None,
) -> tuple[EventService, MagicMock, MagicMock]:
    if org is _DEFAULT:
        org = MagicMock(id=uuid.uuid4())
        org.name = "Live Nation"
    if venue is _DEFAULT:
        venue = MagicMock(id=uuid.uuid4(), city="London")
    session = MagicMock()
    repo = MagicMock()

    async def _insert(event: Event) -> Event:
        event.id = uuid.uuid4()
        event.created_at = datetime.now(timezone.utc)
        return event

    repo.insert = AsyncMock(side_effect=_insert)
    repo.flush = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=existing_event)

    org_repo = MagicMock()
    org_repo.get_by_id = AsyncMock(return_value=org)
    venue_repo = MagicMock()
    venue_repo.get_by_id = AsyncMock(return_value=venue)

    audit = MagicMock()
    audit.record = AsyncMock()

    service = EventService(session, repo, org_repo, venue_repo, audit)
    return service, repo, audit


def _create_kwargs(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "actor_id": uuid.uuid4(),
        "organisation_id": uuid.uuid4(),
        "venue_id": uuid.uuid4(),
        "name": "Concert",
        "description": "Live show",
        "max_tickets_per_user": 4,
    }
    base.update(_times())
    base.update(overrides)
    return base


async def test_create_event_snapshots_org_and_venue() -> None:
    org = MagicMock(id=uuid.uuid4())
    org.name = "Live Nation"
    venue = MagicMock(id=uuid.uuid4(), city="London")
    service, _repo, audit = _service(org=org, venue=venue)
    event = await service.create_event(**_create_kwargs())
    assert event.organiser_name == "Live Nation"
    assert event.venue_city == "London"
    assert event.status == EventStatus.draft
    audit.record.assert_awaited_once()


async def test_create_event_rejects_when_sale_does_not_close_before_start() -> None:
    service, *_ = _service()
    times = _times()
    times["sale_ends_at"] = times["starts_at"] + timedelta(hours=1)
    kwargs = _create_kwargs(**times)
    with pytest.raises(EventError, match="Sale must close"):
        await service.create_event(**kwargs)


async def test_create_event_rejects_inverted_event_window() -> None:
    service, *_ = _service()
    times = _times()
    times["ends_at"] = times["starts_at"] - timedelta(hours=1)
    times["sale_ends_at"] = times["ends_at"] - timedelta(hours=1)
    kwargs = _create_kwargs(**times)
    with pytest.raises(EventError, match="before it ends"):
        await service.create_event(**kwargs)


async def test_create_event_rejects_max_tickets_out_of_range() -> None:
    service, *_ = _service()
    with pytest.raises(EventError, match="max_tickets_per_user"):
        await service.create_event(**_create_kwargs(max_tickets_per_user=21))


async def test_create_event_requires_existing_org() -> None:
    service, *_ = _service(org=None)
    with pytest.raises(EventError, match="Organisation"):
        await service.create_event(**_create_kwargs())


async def test_create_event_requires_existing_venue() -> None:
    service, *_ = _service(venue=None)
    with pytest.raises(EventError, match="Venue"):
        await service.create_event(**_create_kwargs())


async def test_update_event_only_allowed_for_drafts() -> None:
    times = _times()
    event = Event(
        id=uuid.uuid4(),
        organisation_id=uuid.uuid4(),
        venue_id=uuid.uuid4(),
        name="x",
        description=None,
        starts_at=times["starts_at"],
        ends_at=times["ends_at"],
        sale_starts_at=times["sale_starts_at"],
        sale_ends_at=times["sale_ends_at"],
        max_tickets_per_user=4,
        status=EventStatus.published,
        organiser_name="o",
        venue_city="c",
    )
    service, *_ = _service(existing_event=event)
    with pytest.raises(EventError, match="draft"):
        await service.update_event(
            actor_id=uuid.uuid4(), event_id=event.id, changes={"name": "y"}
        )


async def test_update_event_rejects_unknown_field() -> None:
    times = _times()
    event = Event(
        id=uuid.uuid4(),
        organisation_id=uuid.uuid4(),
        venue_id=uuid.uuid4(),
        name="x",
        description=None,
        starts_at=times["starts_at"],
        ends_at=times["ends_at"],
        sale_starts_at=times["sale_starts_at"],
        sale_ends_at=times["sale_ends_at"],
        max_tickets_per_user=4,
        status=EventStatus.draft,
        organiser_name="o",
        venue_city="c",
    )
    service, *_ = _service(existing_event=event)
    with pytest.raises(EventError, match="Cannot edit"):
        await service.update_event(
            actor_id=uuid.uuid4(), event_id=event.id, changes={"status": "published"}
        )
