import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import fakeredis.aioredis
import pytest
import pytest_asyncio

from com.qode.qrew.v1.service.core.locking import lock as lock_module
from com.qode.qrew.v1.service.models.event import EventStatus
from com.qode.qrew.v1.service.models.reservation import (
    Reservation,
    ReservationStatus,
)
from com.qode.qrew.v1.service.models.ticket import Ticket, TicketState
from com.qode.qrew.v1.service.models.ticket_type import TicketType
from com.qode.qrew.v1.service.services.reservation import (
    ReservationError,
    ReservationService,
)


@pytest_asyncio.fixture(autouse=True)
async def _fake_redis_for_locks() -> Any:  # pyright: ignore[reportUnusedFunction]
    fake = fakeredis.aioredis.FakeRedis()
    previous = lock_module._ClientState.client  # pyright: ignore[reportPrivateUsage]
    lock_module._ClientState.client = fake  # pyright: ignore[reportPrivateUsage]
    try:
        yield fake
    finally:
        await fake.aclose()
        lock_module._ClientState.client = previous  # pyright: ignore[reportPrivateUsage]


_DEFAULT = object()


def _event(
    *,
    status: EventStatus = EventStatus.published,
    max_tickets_per_user: int = 4,
) -> MagicMock:
    now = datetime.now(timezone.utc)
    event = MagicMock()
    event.id = uuid.uuid4()
    event.status = status
    event.max_tickets_per_user = max_tickets_per_user
    event.sale_starts_at = now - timedelta(hours=1)
    event.sale_ends_at = now + timedelta(hours=1)
    return event


def _tier(*, capacity: int = 100, reserved_count: int = 0) -> TicketType:
    tier = TicketType(
        id=uuid.uuid4(),
        event_id=uuid.uuid4(),
        name="general",
        description=None,
        capacity=capacity,
        reserved_count=reserved_count,
        price_cents=5000,
        currency="EUR",
        position=0,
    )
    return tier


def _service(
    *,
    event: Any = _DEFAULT,
    tier: Any = _DEFAULT,
    held_quantity: int = 0,
    tier_busy: bool = False,
) -> tuple[ReservationService, MagicMock, MagicMock, list[Reservation]]:
    if event is _DEFAULT:
        event = _event()
    if tier is _DEFAULT:
        tier = _tier()
        tier.event_id = event.id

    session = MagicMock()
    added: list[Any] = []
    session.add = MagicMock(side_effect=added.append)

    async def _flush() -> None:
        return None

    session.flush = AsyncMock(side_effect=_flush)

    async def _execute(*_args: Any, **_kwargs: Any) -> Any:
        if tier_busy:
            from sqlalchemy.exc import DBAPIError

            raise DBAPIError("locked", {}, Exception("locked"))
        result = MagicMock()
        if tier is None:
            result.mappings.return_value.first.return_value = None
        else:
            result.mappings.return_value.first.return_value = {"id": tier.id}
        return result

    session.execute = AsyncMock(side_effect=_execute)

    event_repo = MagicMock()
    event_repo.get_by_id = AsyncMock(return_value=event)

    tier_repo = MagicMock()
    tier_repo.get_by_id = AsyncMock(return_value=tier)

    inserted: list[Reservation] = []

    async def _insert(reservation: Reservation) -> Reservation:
        reservation.id = uuid.uuid4()
        reservation.created_at = datetime.now(timezone.utc)
        inserted.append(reservation)
        return reservation

    repo = MagicMock()

    async def _get_by_id(rid: uuid.UUID) -> Reservation | None:
        return next((r for r in inserted if r.id == rid), None)

    repo.get_by_id = AsyncMock(side_effect=_get_by_id)
    repo.insert = AsyncMock(side_effect=_insert)
    repo.flush = AsyncMock()
    repo.list_tickets = AsyncMock(return_value=[])
    repo.active_quantity_for_user = AsyncMock(return_value=held_quantity)

    audit = MagicMock()
    audit.record = AsyncMock()

    service = ReservationService(session, repo, event_repo, tier_repo, audit)
    return service, session, repo, inserted


async def test_reserve_creates_reservation_and_tickets() -> None:
    event = _event()
    tier = _tier(capacity=100, reserved_count=0)
    tier.event_id = event.id
    service, session, _repo, inserted = _service(event=event, tier=tier)
    reservation = await service.reserve(
        user_id=uuid.uuid4(),
        event_id=event.id,
        ticket_type_id=tier.id,
        quantity=2,
    )
    assert reservation.status == ReservationStatus.reserved
    assert tier.reserved_count == 2
    ticket_adds = [
        c for c in session.add.call_args_list if isinstance(c.args[0], Ticket)
    ]
    assert len(ticket_adds) == 2
    assert all(t.args[0].state == TicketState.reserved for t in ticket_adds)
    assert len(inserted) == 1


async def test_reserve_rejects_over_capacity() -> None:
    event = _event()
    tier = _tier(capacity=5, reserved_count=4)
    tier.event_id = event.id
    service, *_ = _service(event=event, tier=tier)
    with pytest.raises(ReservationError, match="capacity"):
        await service.reserve(
            user_id=uuid.uuid4(),
            event_id=event.id,
            ticket_type_id=tier.id,
            quantity=2,
        )


async def test_reserve_rejects_when_per_user_limit_would_breach() -> None:
    event = _event(max_tickets_per_user=4)
    tier = _tier()
    tier.event_id = event.id
    service, *_ = _service(event=event, tier=tier, held_quantity=3)
    with pytest.raises(ReservationError, match="per-user"):
        await service.reserve(
            user_id=uuid.uuid4(),
            event_id=event.id,
            ticket_type_id=tier.id,
            quantity=2,
        )


async def test_reserve_rejects_unpublished_event() -> None:
    event = _event(status=EventStatus.draft)
    tier = _tier()
    tier.event_id = event.id
    service, *_ = _service(event=event, tier=tier)
    with pytest.raises(ReservationError, match="not on sale"):
        await service.reserve(
            user_id=uuid.uuid4(),
            event_id=event.id,
            ticket_type_id=tier.id,
            quantity=1,
        )


async def test_reserve_rejects_quantity_above_event_cap() -> None:
    event = _event(max_tickets_per_user=4)
    tier = _tier()
    tier.event_id = event.id
    service, *_ = _service(event=event, tier=tier)
    with pytest.raises(ReservationError, match="per-user"):
        await service.reserve(
            user_id=uuid.uuid4(),
            event_id=event.id,
            ticket_type_id=tier.id,
            quantity=5,
        )


async def test_reserve_returns_409_when_tier_locked() -> None:
    event = _event()
    tier = _tier()
    tier.event_id = event.id
    service, *_ = _service(event=event, tier=tier, tier_busy=True)
    from com.qode.qrew.v1.service.services.reservation import TierBusyError

    with pytest.raises(TierBusyError):
        await service.reserve(
            user_id=uuid.uuid4(),
            event_id=event.id,
            ticket_type_id=tier.id,
            quantity=1,
        )


async def test_cancel_flips_reservation_and_frees_capacity() -> None:
    event = _event()
    tier = _tier(capacity=10, reserved_count=3)
    tier.event_id = event.id
    user_id = uuid.uuid4()
    service, _session, repo, inserted = _service(event=event, tier=tier)
    reservation = await service.reserve(
        user_id=user_id, event_id=event.id, ticket_type_id=tier.id, quantity=2
    )
    held_tickets = [
        Ticket(
            id=uuid.uuid4(),
            reservation_id=reservation.id,
            event_id=event.id,
            ticket_type_id=tier.id,
            owner_user_id=user_id,
            state=TicketState.reserved,
        )
        for _ in range(2)
    ]
    repo.list_tickets = AsyncMock(return_value=held_tickets)
    cancelled = await service.cancel(actor_id=user_id, reservation_id=reservation.id)
    assert cancelled.status == ReservationStatus.cancelled
    assert tier.reserved_count == 3  # was 5 after reserve, back to 3 after cancel
    assert all(t.state == TicketState.cancelled for t in held_tickets)
    del inserted


async def test_cancel_rejects_paid_reservation() -> None:
    event = _event()
    tier = _tier()
    tier.event_id = event.id
    user_id = uuid.uuid4()
    service, _session, repo, _ = _service(event=event, tier=tier)
    reservation = await service.reserve(
        user_id=user_id, event_id=event.id, ticket_type_id=tier.id, quantity=1
    )
    reservation.status = ReservationStatus.paid
    repo.get_by_id = AsyncMock(return_value=reservation)
    with pytest.raises(ReservationError, match="refunded"):
        await service.cancel(actor_id=user_id, reservation_id=reservation.id)


async def test_get_for_user_rejects_other_users_reservation() -> None:
    event = _event()
    tier = _tier()
    tier.event_id = event.id
    owner = uuid.uuid4()
    intruder = uuid.uuid4()
    service, _session, _repo, _ = _service(event=event, tier=tier)
    reservation = await service.reserve(
        user_id=owner, event_id=event.id, ticket_type_id=tier.id, quantity=1
    )
    with pytest.raises(ReservationError, match="not found"):
        await service.get_for_user(actor_id=intruder, reservation_id=reservation.id)
