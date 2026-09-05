# tests ticket type
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from com.qode.qrew.v1.catalog.models.event import EventStatus
from com.qode.qrew.v1.catalog.services.application.ticket_type import (
    TicketTypeError,
    TicketTypeService,
    _validate_capacity,
    _validate_currency,
    _validate_name,
    _validate_price,
)
from conftest import make_event, make_fake_settings, make_redlock_cm, make_ticket_type

_MOD = "com.qode.qrew.v1.catalog.services.application.ticket_type"
_PATCH_REDLOCK = f"{_MOD}.redlock"
_PATCH_SETTINGS = f"{_MOD}.settings"


# handles make svc
def _make_svc(
    *,
    event: object = None,
    ticket_type: object = None,
    name_conflict: object = None,
) -> tuple[TicketTypeService, MagicMock]:
    event_repo = MagicMock()
    event_repo.get_by_id = AsyncMock(return_value=event)

    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=ticket_type)
    repo.get_by_event_and_name = AsyncMock(return_value=name_conflict)
    repo.insert = AsyncMock(side_effect=lambda t: t)
    repo.flush = AsyncMock()

    audit = AsyncMock()
    audit.record = AsyncMock()

    session = MagicMock()
    session.add = MagicMock()

    svc = TicketTypeService(session=session, event_repo=event_repo, repo=repo, audit=audit)
    return svc, repo


class TestValidateName:
    # verifies that raises when starts with digit
    def test_raises_when_starts_with_digit(self) -> None:
        with pytest.raises(TicketTypeError, match="lowercase"):
            _validate_name("1general")

    # verifies that raises when contains uppercase
    def test_raises_when_contains_uppercase(self) -> None:
        with pytest.raises(TicketTypeError):
            _validate_name("General")

    # verifies that raises when too long
    def test_raises_when_too_long(self) -> None:
        with pytest.raises(TicketTypeError):
            _validate_name("a" * 33)

    # verifies that valid names pass
    def test_valid_names_pass(self) -> None:
        _validate_name("general")
        _validate_name("vip_tier")
        _validate_name("a1b2c3")


class TestValidateCapacity:
    # verifies that raises when zero
    def test_raises_when_zero(self) -> None:
        with pytest.raises(TicketTypeError, match="between 1"):
            _validate_capacity(0)

    # verifies that raises when over limit
    def test_raises_when_over_limit(self) -> None:
        with pytest.raises(TicketTypeError):
            _validate_capacity(100_001)

    # verifies that valid passes
    def test_valid_passes(self) -> None:
        _validate_capacity(1)
        _validate_capacity(100_000)


class TestValidatePrice:
    # verifies that raises when negative
    def test_raises_when_negative(self) -> None:
        with pytest.raises(TicketTypeError, match="between 0"):
            _validate_price(-1)

    # verifies that raises when over limit
    def test_raises_when_over_limit(self) -> None:
        with pytest.raises(TicketTypeError):
            _validate_price(10_000_001)

    # verifies that zero is valid
    def test_zero_is_valid(self) -> None:
        _validate_price(0)


class TestValidateCurrency:
    # verifies that raises when unknown
    def test_raises_when_unknown(self) -> None:
        with pytest.raises(TicketTypeError, match="Currency"):
            _validate_currency("XYZ")

    # verifies that valid currencies pass
    def test_valid_currencies_pass(self) -> None:
        _validate_currency("EUR")
        _validate_currency("USD")
        _validate_currency("GBP")


class TestTicketTypeServiceCreate:
    # verifies that raises on invalid name
    async def test_raises_on_invalid_name(self, actor_id: uuid.UUID, event_id: uuid.UUID) -> None:
        svc, _ = _make_svc()
        with pytest.raises(TicketTypeError, match="lowercase"):
            await svc.create(
                actor_id=actor_id,
                event_id=event_id,
                name="1bad",
                description=None,
                capacity=100,
                price_cents=1000,
                currency="EUR",
                position=0,
            )

    # verifies that raises on invalid currency
    async def test_raises_on_invalid_currency(
        self, actor_id: uuid.UUID, event_id: uuid.UUID
    ) -> None:
        svc, _ = _make_svc()
        with pytest.raises(TicketTypeError, match="Currency"):
            await svc.create(
                actor_id=actor_id,
                event_id=event_id,
                name="general",
                description=None,
                capacity=100,
                price_cents=1000,
                currency="BTC",
                position=0,
            )

    # verifies that raises when event not found
    async def test_raises_when_event_not_found(
        self, actor_id: uuid.UUID, event_id: uuid.UUID
    ) -> None:
        svc, _ = _make_svc(event=None)
        with (
            patch(_PATCH_REDLOCK, return_value=make_redlock_cm()),
            patch(_PATCH_SETTINGS, make_fake_settings()),
            pytest.raises(TicketTypeError, match="Event not found."),
        ):
            await svc.create(
                actor_id=actor_id,
                event_id=event_id,
                name="general",
                description=None,
                capacity=100,
                price_cents=1000,
                currency="EUR",
                position=0,
            )

    # verifies that raises when event cancelled
    async def test_raises_when_event_cancelled(
        self, actor_id: uuid.UUID, event_id: uuid.UUID
    ) -> None:
        event = make_event(event_id=event_id, status=EventStatus.cancelled)
        svc, _ = _make_svc(event=event)
        with (
            patch(_PATCH_REDLOCK, return_value=make_redlock_cm()),
            patch(_PATCH_SETTINGS, make_fake_settings()),
            pytest.raises(TicketTypeError, match="cancelled"),
        ):
            await svc.create(
                actor_id=actor_id,
                event_id=event_id,
                name="general",
                description=None,
                capacity=100,
                price_cents=1000,
                currency="EUR",
                position=0,
            )

    # verifies that raises when name already exists
    async def test_raises_when_name_already_exists(
        self, actor_id: uuid.UUID, event_id: uuid.UUID
    ) -> None:
        event = make_event(event_id=event_id, status=EventStatus.draft)
        existing = make_ticket_type(event_id=event_id, name="general")
        svc, _ = _make_svc(event=event, name_conflict=existing)
        with (
            patch(_PATCH_REDLOCK, return_value=make_redlock_cm()),
            patch(_PATCH_SETTINGS, make_fake_settings()),
            pytest.raises(TicketTypeError, match="already taken"),
        ):
            await svc.create(
                actor_id=actor_id,
                event_id=event_id,
                name="general",
                description=None,
                capacity=100,
                price_cents=1000,
                currency="EUR",
                position=0,
            )

    # verifies that creates ticket type
    async def test_creates_ticket_type(self, actor_id: uuid.UUID, event_id: uuid.UUID) -> None:
        event = make_event(event_id=event_id, status=EventStatus.draft)
        svc, repo = _make_svc(event=event, name_conflict=None)
        with (
            patch(_PATCH_REDLOCK, return_value=make_redlock_cm()),
            patch(_PATCH_SETTINGS, make_fake_settings()),
        ):
            result = await svc.create(
                actor_id=actor_id,
                event_id=event_id,
                name="vip",
                description=None,
                capacity=200,
                price_cents=5000,
                currency="EUR",
                position=1,
            )
        assert result.name == "vip"
        assert result.capacity == 200
        repo.insert.assert_awaited_once()


class TestTicketTypeServiceUpdate:
    # verifies that raises on unknown fields
    async def test_raises_on_unknown_fields(
        self, actor_id: uuid.UUID, event_id: uuid.UUID, ticket_type_id: uuid.UUID
    ) -> None:
        svc, _ = _make_svc()
        with pytest.raises(TicketTypeError, match="Cannot edit"):
            await svc.update(
                actor_id=actor_id,
                event_id=event_id,
                ticket_type_id=ticket_type_id,
                changes={"currency": "EUR"},
            )

    # verifies that raises when not found
    async def test_raises_when_not_found(
        self, actor_id: uuid.UUID, event_id: uuid.UUID, ticket_type_id: uuid.UUID
    ) -> None:
        svc, _ = _make_svc(ticket_type=None)
        with (
            patch(_PATCH_REDLOCK, return_value=make_redlock_cm()),
            patch(_PATCH_SETTINGS, make_fake_settings()),
            pytest.raises(TicketTypeError, match="not found"),
        ):
            await svc.update(
                actor_id=actor_id,
                event_id=event_id,
                ticket_type_id=ticket_type_id,
                changes={"name": "vip"},
            )

    # verifies that raises when ticket type belongs to other event
    async def test_raises_when_ticket_type_belongs_to_other_event(
        self, actor_id: uuid.UUID, event_id: uuid.UUID, ticket_type_id: uuid.UUID
    ) -> None:
        tt = make_ticket_type(ticket_type_id=ticket_type_id, event_id=uuid.uuid4())
        svc, _ = _make_svc(ticket_type=tt)
        with (
            patch(_PATCH_REDLOCK, return_value=make_redlock_cm()),
            patch(_PATCH_SETTINGS, make_fake_settings()),
            pytest.raises(TicketTypeError, match="not found"),
        ):
            await svc.update(
                actor_id=actor_id,
                event_id=event_id,
                ticket_type_id=ticket_type_id,
                changes={"name": "vip"},
            )

    # verifies that raises when capacity decreases
    async def test_raises_when_capacity_decreases(
        self, actor_id: uuid.UUID, event_id: uuid.UUID, ticket_type_id: uuid.UUID
    ) -> None:
        event = make_event(event_id=event_id, status=EventStatus.published)
        tt = make_ticket_type(ticket_type_id=ticket_type_id, event_id=event_id, capacity=500)
        svc, _ = _make_svc(event=event, ticket_type=tt)
        with (
            patch(_PATCH_REDLOCK, return_value=make_redlock_cm()),
            patch(_PATCH_SETTINGS, make_fake_settings()),
            pytest.raises(TicketTypeError, match="only increase"),
        ):
            await svc.update(
                actor_id=actor_id,
                event_id=event_id,
                ticket_type_id=ticket_type_id,
                changes={"capacity": 100},
            )

    # verifies that raises on name conflict
    async def test_raises_on_name_conflict(
        self, actor_id: uuid.UUID, event_id: uuid.UUID, ticket_type_id: uuid.UUID
    ) -> None:
        event = make_event(event_id=event_id, status=EventStatus.published)
        tt = make_ticket_type(ticket_type_id=ticket_type_id, event_id=event_id, name="general")
        other = make_ticket_type(event_id=event_id, name="vip")
        svc, _ = _make_svc(event=event, ticket_type=tt, name_conflict=other)
        with (
            patch(_PATCH_REDLOCK, return_value=make_redlock_cm()),
            patch(_PATCH_SETTINGS, make_fake_settings()),
            pytest.raises(TicketTypeError, match="already taken"),
        ):
            await svc.update(
                actor_id=actor_id,
                event_id=event_id,
                ticket_type_id=ticket_type_id,
                changes={"name": "vip"},
            )

    # verifies that updates fields and flushes
    async def test_updates_fields_and_flushes(
        self, actor_id: uuid.UUID, event_id: uuid.UUID, ticket_type_id: uuid.UUID
    ) -> None:
        event = make_event(event_id=event_id, status=EventStatus.published)
        tt = make_ticket_type(ticket_type_id=ticket_type_id, event_id=event_id, price_cents=1000)
        svc, repo = _make_svc(event=event, ticket_type=tt, name_conflict=None)
        with (
            patch(_PATCH_REDLOCK, return_value=make_redlock_cm()),
            patch(_PATCH_SETTINGS, make_fake_settings()),
        ):
            result = await svc.update(
                actor_id=actor_id,
                event_id=event_id,
                ticket_type_id=ticket_type_id,
                changes={"price_cents": 2000},
            )
        assert result.price_cents == 2000
        repo.flush.assert_awaited_once()


class TestTicketTypeServiceDelete:
    # verifies that raises when not found
    async def test_raises_when_not_found(
        self, actor_id: uuid.UUID, event_id: uuid.UUID, ticket_type_id: uuid.UUID
    ) -> None:
        svc, _ = _make_svc(ticket_type=None)
        with (
            patch(_PATCH_REDLOCK, return_value=make_redlock_cm()),
            patch(_PATCH_SETTINGS, make_fake_settings()),
            pytest.raises(TicketTypeError, match="not found"),
        ):
            await svc.delete(actor_id=actor_id, event_id=event_id, ticket_type_id=ticket_type_id)

    # verifies that raises when has live reservations
    async def test_raises_when_has_live_reservations(
        self, actor_id: uuid.UUID, event_id: uuid.UUID, ticket_type_id: uuid.UUID
    ) -> None:
        event = make_event(event_id=event_id, status=EventStatus.published)
        tt = make_ticket_type(ticket_type_id=ticket_type_id, event_id=event_id, reserved_count=5)
        svc, _ = _make_svc(event=event, ticket_type=tt)
        with (
            patch(_PATCH_REDLOCK, return_value=make_redlock_cm()),
            patch(_PATCH_SETTINGS, make_fake_settings()),
            pytest.raises(TicketTypeError, match="live reservations"),
        ):
            await svc.delete(actor_id=actor_id, event_id=event_id, ticket_type_id=ticket_type_id)

    # verifies that sets deleted at and flushes
    async def test_sets_deleted_at_and_flushes(
        self, actor_id: uuid.UUID, event_id: uuid.UUID, ticket_type_id: uuid.UUID
    ) -> None:
        event = make_event(event_id=event_id, status=EventStatus.published)
        tt = make_ticket_type(ticket_type_id=ticket_type_id, event_id=event_id, reserved_count=0)
        svc, repo = _make_svc(event=event, ticket_type=tt)
        with (
            patch(_PATCH_REDLOCK, return_value=make_redlock_cm()),
            patch(_PATCH_SETTINGS, make_fake_settings()),
        ):
            await svc.delete(actor_id=actor_id, event_id=event_id, ticket_type_id=ticket_type_id)
        assert tt.deleted_at is not None
        repo.flush.assert_awaited_once()
