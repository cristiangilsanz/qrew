import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import fakeredis.aioredis
import pytest
import pytest_asyncio

from com.qode.qrew.v1.service.core.locking import lock as lock_module
from com.qode.qrew.v1.service.models.event import EventStatus
from com.qode.qrew.v1.service.models.ticket_type import TicketType
from com.qode.qrew.v1.service.services.ticket_type import (
    TicketTypeError,
    TicketTypeService,
)


@pytest_asyncio.fixture(autouse=True)
async def _fake_redis_for_locks() -> Any:  # pyright: ignore[reportUnusedFunction]
    """Swap the locking module's shared Redis client for an in-memory fake."""
    fake = fakeredis.aioredis.FakeRedis()
    previous = lock_module._ClientState.client  # pyright: ignore[reportPrivateUsage]
    lock_module._ClientState.client = fake  # pyright: ignore[reportPrivateUsage]
    try:
        yield fake
    finally:
        await fake.aclose()
        lock_module._ClientState.client = previous  # pyright: ignore[reportPrivateUsage]


def _service(
    *,
    event_status: EventStatus = EventStatus.draft,
    existing_named: TicketType | None = None,
    existing_by_id: TicketType | None = None,
) -> tuple[TicketTypeService, MagicMock, MagicMock]:
    event_repo = MagicMock()
    event = MagicMock(id=uuid.uuid4(), status=event_status)
    event_repo.get_by_id = AsyncMock(return_value=event)

    repo = MagicMock()
    repo.get_by_event_and_name = AsyncMock(return_value=existing_named)
    repo.get_by_id = AsyncMock(return_value=existing_by_id)

    async def _insert(ticket_type: TicketType) -> TicketType:
        ticket_type.id = uuid.uuid4()
        return ticket_type

    repo.insert = AsyncMock(side_effect=_insert)
    repo.flush = AsyncMock()

    audit = MagicMock()
    audit.record = AsyncMock()
    service = TicketTypeService(event_repo, repo, audit)
    return service, repo, audit


def _create_kwargs(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "actor_id": uuid.uuid4(),
        "event_id": uuid.uuid4(),
        "name": "general",
        "description": "General admission",
        "capacity": 500,
        "price_cents": 5000,
        "currency": "EUR",
        "position": 0,
    }
    base.update(overrides)
    return base


async def test_create_persists_and_audits() -> None:
    service, _repo, audit = _service()
    ticket_type = await service.create(**_create_kwargs())
    assert ticket_type.name == "general"
    audit.record.assert_awaited_once()


async def test_create_rejects_cancelled_event() -> None:
    service, *_ = _service(event_status=EventStatus.cancelled)
    with pytest.raises(TicketTypeError, match="cancelled"):
        await service.create(**_create_kwargs())


async def test_create_rejects_invalid_name() -> None:
    service, *_ = _service()
    with pytest.raises(TicketTypeError, match="lowercase"):
        await service.create(**_create_kwargs(name="VIP!"))


async def test_create_rejects_unsupported_currency() -> None:
    service, *_ = _service()
    with pytest.raises(TicketTypeError, match="Currency"):
        await service.create(**_create_kwargs(currency="JPY"))


async def test_create_rejects_duplicate_name() -> None:
    existing = MagicMock(spec=TicketType)
    service, *_ = _service(existing_named=existing)
    with pytest.raises(TicketTypeError, match="already exists"):
        await service.create(**_create_kwargs())


def _ticket(**overrides: Any) -> TicketType:
    base: dict[str, Any] = {
        "id": uuid.uuid4(),
        "event_id": uuid.uuid4(),
        "name": "general",
        "description": None,
        "capacity": 100,
        "reserved_count": 0,
        "price_cents": 5000,
        "currency": "EUR",
        "position": 0,
    }
    base.update(overrides)
    return TicketType(**base)


async def test_update_refuses_lowering_capacity() -> None:
    existing = _ticket(capacity=100)
    service, *_ = _service(existing_by_id=existing)
    with pytest.raises(TicketTypeError, match="only increase"):
        await service.update(
            actor_id=uuid.uuid4(),
            event_id=existing.event_id,
            ticket_type_id=existing.id,
            changes={"capacity": 50},
        )


async def test_update_allows_raising_capacity() -> None:
    existing = _ticket(capacity=100)
    service, _repo, _audit = _service(existing_by_id=existing)
    updated = await service.update(
        actor_id=uuid.uuid4(),
        event_id=existing.event_id,
        ticket_type_id=existing.id,
        changes={"capacity": 200},
    )
    assert updated.capacity == 200


async def test_update_rejects_unknown_field() -> None:
    existing = _ticket()
    service, *_ = _service(existing_by_id=existing)
    with pytest.raises(TicketTypeError, match="Cannot edit"):
        await service.update(
            actor_id=uuid.uuid4(),
            event_id=existing.event_id,
            ticket_type_id=existing.id,
            changes={"reserved_count": 5},
        )


async def test_delete_blocked_when_reservations_exist() -> None:
    existing = _ticket(reserved_count=1)
    service, *_ = _service(existing_by_id=existing)
    with pytest.raises(TicketTypeError, match="live reservations"):
        await service.delete(
            actor_id=uuid.uuid4(),
            event_id=existing.event_id,
            ticket_type_id=existing.id,
        )


async def test_delete_sets_deleted_at() -> None:
    existing = _ticket(reserved_count=0)
    service, _repo, _audit = _service(existing_by_id=existing)
    await service.delete(
        actor_id=uuid.uuid4(),
        event_id=existing.event_id,
        ticket_type_id=existing.id,
    )
    assert existing.deleted_at is not None
