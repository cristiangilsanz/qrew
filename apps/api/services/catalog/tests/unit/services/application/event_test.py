import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from com.qode.qrew.v1.catalog.models.event import EventStatus
from com.qode.qrew.v1.catalog.services.application.events.event import (
    EventError,
    EventService,
    _validate_max_tickets,
    _validate_windows,
)
from conftest import (
    make_event,
    make_fake_settings,
    make_org,
    make_redlock_cm,
    make_venue,
)

_MOD = "com.qode.qrew.v1.catalog.services.application.events.event"
_PATCH_REDLOCK = f"{_MOD}.redlock"
_PATCH_SETTINGS = f"{_MOD}.settings"
_PATCH_REINDEX = f"{_MOD}.EventService._reindex"


def _make_svc(
    *,
    event: object = None,
    org: object = None,
    venue: object = None,
) -> tuple[EventService, MagicMock]:
    session = MagicMock()
    session.execute = AsyncMock()

    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=event)
    repo.insert = AsyncMock(side_effect=lambda e: e)
    repo.flush = AsyncMock()

    org_repo = MagicMock()
    org_repo.get_by_id = AsyncMock(return_value=org)

    venue_repo = MagicMock()
    venue_repo.get_by_id = AsyncMock(return_value=venue)

    audit = AsyncMock()
    audit.record = AsyncMock()

    svc = EventService(
        session=session, repo=repo, org_repo=org_repo, venue_repo=venue_repo, audit=audit
    )
    return svc, repo


# ── Pure function tests ───────────────────────────────────────────────────────


class TestValidateWindows:
    def test_raises_when_starts_after_ends(self) -> None:
        now = datetime.now(UTC)
        with pytest.raises(EventError, match="start before it ends"):
            _validate_windows(
                starts_at=now + timedelta(hours=4),
                ends_at=now + timedelta(hours=2),
                sale_starts_at=now,
                sale_ends_at=now + timedelta(hours=1),
            )

    def test_raises_when_sale_starts_after_sale_ends(self) -> None:
        now = datetime.now(UTC)
        with pytest.raises(EventError, match="Sale must start before"):
            _validate_windows(
                starts_at=now + timedelta(days=30),
                ends_at=now + timedelta(days=30, hours=4),
                sale_starts_at=now + timedelta(days=5),
                sale_ends_at=now + timedelta(days=1),
            )

    def test_raises_when_sale_closes_after_event_starts(self) -> None:
        now = datetime.now(UTC)
        with pytest.raises(EventError, match="Sale must close before"):
            _validate_windows(
                starts_at=now + timedelta(days=2),
                ends_at=now + timedelta(days=2, hours=4),
                sale_starts_at=now,
                sale_ends_at=now + timedelta(days=3),  # closes after event starts
            )

    def test_valid_windows_pass(self) -> None:
        now = datetime.now(UTC)
        _validate_windows(
            starts_at=now + timedelta(days=30),
            ends_at=now + timedelta(days=30, hours=4),
            sale_starts_at=now + timedelta(days=1),
            sale_ends_at=now + timedelta(days=29),
        )


class TestValidateMaxTickets:
    def test_raises_when_zero(self) -> None:
        with pytest.raises(EventError, match="between 1 and 20"):
            _validate_max_tickets(0)

    def test_raises_when_above_20(self) -> None:
        with pytest.raises(EventError, match="between 1 and 20"):
            _validate_max_tickets(21)

    def test_valid_values_pass(self) -> None:
        _validate_max_tickets(1)
        _validate_max_tickets(10)
        _validate_max_tickets(20)


# ── EventService tests ────────────────────────────────────────────────────────


class TestEventServiceCreate:
    async def test_raises_when_windows_invalid(
        self, actor_id: uuid.UUID, org_id: uuid.UUID, venue_id: uuid.UUID
    ) -> None:
        svc, _ = _make_svc()
        now = datetime.now(UTC)
        with pytest.raises(EventError):
            await svc.create_event(
                actor_id=actor_id,
                organisation_id=org_id,
                venue_id=venue_id,
                name="Bad",
                description=None,
                starts_at=now + timedelta(hours=1),
                ends_at=now,  # ends before starts
                sale_starts_at=now,
                sale_ends_at=now + timedelta(minutes=30),
                max_tickets_per_user=4,
                image_url=None,
            )

    async def test_raises_when_max_tickets_out_of_range(
        self, actor_id: uuid.UUID, org_id: uuid.UUID, venue_id: uuid.UUID
    ) -> None:
        svc, _ = _make_svc()
        now = datetime.now(UTC)
        with pytest.raises(EventError, match="between 1 and 20"):
            await svc.create_event(
                actor_id=actor_id,
                organisation_id=org_id,
                venue_id=venue_id,
                name="Bad",
                description=None,
                starts_at=now + timedelta(days=30),
                ends_at=now + timedelta(days=30, hours=4),
                sale_starts_at=now + timedelta(days=1),
                sale_ends_at=now + timedelta(days=29),
                max_tickets_per_user=25,
                image_url=None,
            )

    async def test_raises_when_org_not_found(
        self, actor_id: uuid.UUID, org_id: uuid.UUID, venue_id: uuid.UUID
    ) -> None:
        svc, _ = _make_svc(org=None)
        now = datetime.now(UTC)
        with pytest.raises(EventError, match="Organisation not found"):
            await svc.create_event(
                actor_id=actor_id,
                organisation_id=org_id,
                venue_id=venue_id,
                name="Concert",
                description=None,
                starts_at=now + timedelta(days=30),
                ends_at=now + timedelta(days=30, hours=4),
                sale_starts_at=now + timedelta(days=1),
                sale_ends_at=now + timedelta(days=29),
                max_tickets_per_user=4,
                image_url=None,
            )

    async def test_raises_when_venue_not_found(
        self, actor_id: uuid.UUID, org_id: uuid.UUID, venue_id: uuid.UUID
    ) -> None:
        svc, _ = _make_svc(org=make_org(org_id=org_id), venue=None)
        now = datetime.now(UTC)
        with pytest.raises(EventError, match="Venue not found"):
            await svc.create_event(
                actor_id=actor_id,
                organisation_id=org_id,
                venue_id=venue_id,
                name="Concert",
                description=None,
                starts_at=now + timedelta(days=30),
                ends_at=now + timedelta(days=30, hours=4),
                sale_starts_at=now + timedelta(days=1),
                sale_ends_at=now + timedelta(days=29),
                max_tickets_per_user=4,
                image_url=None,
            )

    async def test_creates_event_with_draft_status(
        self, actor_id: uuid.UUID, org_id: uuid.UUID, venue_id: uuid.UUID
    ) -> None:
        org = make_org(org_id=org_id)
        venue = make_venue(venue_id=venue_id)
        svc, repo = _make_svc(org=org, venue=venue)
        now = datetime.now(UTC)
        result = await svc.create_event(
            actor_id=actor_id,
            organisation_id=org_id,
            venue_id=venue_id,
            name="Concert",
            description=None,
            starts_at=now + timedelta(days=30),
            ends_at=now + timedelta(days=30, hours=4),
            sale_starts_at=now + timedelta(days=1),
            sale_ends_at=now + timedelta(days=29),
            max_tickets_per_user=4,
            image_url=None,
        )
        assert result.status == EventStatus.draft
        assert result.name == "Concert"
        repo.insert.assert_awaited_once()


class TestEventServiceUpdate:
    async def test_raises_when_not_found(self, actor_id: uuid.UUID, event_id: uuid.UUID) -> None:
        svc, _ = _make_svc(event=None)
        with pytest.raises(EventError, match="not found"):
            await svc.update_event(actor_id=actor_id, event_id=event_id, changes={"name": "X"})

    async def test_raises_when_not_draft(self, actor_id: uuid.UUID, event_id: uuid.UUID) -> None:
        event = make_event(event_id=event_id, status=EventStatus.published)
        svc, _ = _make_svc(event=event)
        with pytest.raises(EventError, match="draft"):
            await svc.update_event(actor_id=actor_id, event_id=event_id, changes={"name": "X"})

    async def test_raises_when_unknown_fields(
        self, actor_id: uuid.UUID, event_id: uuid.UUID
    ) -> None:
        event = make_event(event_id=event_id, status=EventStatus.draft)
        svc, _ = _make_svc(event=event)
        with pytest.raises(EventError, match="Cannot edit fields"):
            await svc.update_event(
                actor_id=actor_id,
                event_id=event_id,
                changes={"organisation_id": uuid.uuid4()},
            )

    async def test_raises_when_updated_windows_invalid(
        self, actor_id: uuid.UUID, event_id: uuid.UUID
    ) -> None:
        event = make_event(event_id=event_id, status=EventStatus.draft)
        # Set ends_at to before starts_at via change
        svc, _ = _make_svc(event=event)
        with pytest.raises(EventError):
            await svc.update_event(
                actor_id=actor_id,
                event_id=event_id,
                changes={"ends_at": event.starts_at - timedelta(hours=1)},
            )

    async def test_updates_name_and_flushes(self, actor_id: uuid.UUID, event_id: uuid.UUID) -> None:
        event = make_event(event_id=event_id, status=EventStatus.draft)
        svc, repo = _make_svc(event=event)
        result = await svc.update_event(
            actor_id=actor_id, event_id=event_id, changes={"name": "New Name"}
        )
        assert result.name == "New Name"
        repo.flush.assert_awaited_once()


class TestEventServicePublish:
    async def test_raises_when_not_found(self, actor_id: uuid.UUID, event_id: uuid.UUID) -> None:
        svc, _ = _make_svc(event=None)
        with (
            patch(_PATCH_REDLOCK, return_value=make_redlock_cm()),
            patch(_PATCH_SETTINGS, make_fake_settings()),
            patch(_PATCH_REINDEX, new=AsyncMock()),
            pytest.raises(EventError, match="not found"),
        ):
            await svc.publish_event(actor_id=actor_id, event_id=event_id)

    async def test_returns_early_when_already_published(
        self, actor_id: uuid.UUID, event_id: uuid.UUID
    ) -> None:
        event = make_event(event_id=event_id, status=EventStatus.published)
        svc, repo = _make_svc(event=event)
        with (
            patch(_PATCH_REDLOCK, return_value=make_redlock_cm()),
            patch(_PATCH_SETTINGS, make_fake_settings()),
            patch(_PATCH_REINDEX, new=AsyncMock()),
        ):
            result = await svc.publish_event(actor_id=actor_id, event_id=event_id)
        assert result is event
        repo.flush.assert_not_awaited()

    async def test_raises_when_not_draft(self, actor_id: uuid.UUID, event_id: uuid.UUID) -> None:
        event = make_event(event_id=event_id, status=EventStatus.cancelled)
        svc, _ = _make_svc(event=event)
        with (
            patch(_PATCH_REDLOCK, return_value=make_redlock_cm()),
            patch(_PATCH_SETTINGS, make_fake_settings()),
            patch(_PATCH_REINDEX, new=AsyncMock()),
            pytest.raises(EventError, match="draft"),
        ):
            await svc.publish_event(actor_id=actor_id, event_id=event_id)

    async def test_publishes_and_flushes(self, actor_id: uuid.UUID, event_id: uuid.UUID) -> None:
        event = make_event(event_id=event_id, status=EventStatus.draft)
        svc, repo = _make_svc(event=event)
        with (
            patch(_PATCH_REDLOCK, return_value=make_redlock_cm()),
            patch(_PATCH_SETTINGS, make_fake_settings()),
            patch(_PATCH_REINDEX, new=AsyncMock()),
        ):
            result = await svc.publish_event(actor_id=actor_id, event_id=event_id)
        assert result.status == EventStatus.published
        assert result.published_at is not None
        repo.flush.assert_awaited()


class TestEventServiceCancel:
    async def test_raises_when_not_found(self, actor_id: uuid.UUID, event_id: uuid.UUID) -> None:
        svc, _ = _make_svc(event=None)
        with (
            patch(_PATCH_REDLOCK, return_value=make_redlock_cm()),
            patch(_PATCH_SETTINGS, make_fake_settings()),
            patch(_PATCH_REINDEX, new=AsyncMock()),
            pytest.raises(EventError, match="not found"),
        ):
            await svc.cancel_event(actor_id=actor_id, event_id=event_id)

    async def test_returns_early_when_already_cancelled(
        self, actor_id: uuid.UUID, event_id: uuid.UUID
    ) -> None:
        event = make_event(event_id=event_id, status=EventStatus.cancelled)
        svc, repo = _make_svc(event=event)
        with (
            patch(_PATCH_REDLOCK, return_value=make_redlock_cm()),
            patch(_PATCH_SETTINGS, make_fake_settings()),
            patch(_PATCH_REINDEX, new=AsyncMock()),
        ):
            result = await svc.cancel_event(actor_id=actor_id, event_id=event_id)
        assert result is event
        repo.flush.assert_not_awaited()

    async def test_cancels_and_flushes(self, actor_id: uuid.UUID, event_id: uuid.UUID) -> None:
        event = make_event(event_id=event_id, status=EventStatus.published)
        svc, repo = _make_svc(event=event)
        with (
            patch(_PATCH_REDLOCK, return_value=make_redlock_cm()),
            patch(_PATCH_SETTINGS, make_fake_settings()),
            patch(_PATCH_REINDEX, new=AsyncMock()),
        ):
            result = await svc.cancel_event(actor_id=actor_id, event_id=event_id)
        assert result.status == EventStatus.cancelled
        assert result.cancelled_at is not None
        repo.flush.assert_awaited()
