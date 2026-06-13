import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import fakeredis.aioredis
import jwt
import pytest_asyncio

from com.qode.qrew.v1.service.core.auth import jwt_keys
from com.qode.qrew.v1.service.core.locking import lock as lock_module
from com.qode.qrew.v1.service.models.audit.audit import AuditAction
from com.qode.qrew.v1.service.models.ticket import Ticket, TicketState
from com.qode.qrew.v1.service.services.audit import AuditService
from com.qode.qrew.v1.service.services.entry import EntryReason, validate_entry
from com.qode.qrew.v1.service.settings import settings


@pytest_asyncio.fixture
async def redis_client() -> Any:
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    try:
        yield client
    finally:
        await client.aclose()


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


def _mint_ticket_jwt(
    *,
    ticket_id: uuid.UUID,
    event_id: uuid.UUID,
    venue_id: uuid.UUID,
    aud: str | None = None,
    expired: bool = False,
    jti: str | None = None,
) -> str:
    now = datetime.now(UTC)
    iat = now - timedelta(seconds=5)
    exp = now - timedelta(seconds=1) if expired else now + timedelta(seconds=60)
    claims: dict[str, Any] = {
        "sub": str(uuid.uuid4()),
        "ticket_id": str(ticket_id),
        "event_id": str(event_id),
        "venue_id": str(venue_id),
        "device_id": str(uuid.uuid4()),
        "jti": jti or uuid.uuid4().hex,
        "iat": iat,
        "exp": exp,
        "aud": aud if aud is not None else settings.ticket_qr_audience,
    }
    return jwt_keys.sign(jwt_keys.TICKET_QR, claims)


def _scanner(venue_id: uuid.UUID) -> MagicMock:
    s = MagicMock()
    s.id = uuid.uuid4()
    s.venue_id = venue_id
    s.is_active = True
    return s


def _ticket(
    *,
    ticket_id: uuid.UUID,
    event_id: uuid.UUID,
    state: TicketState = TicketState.issued,
) -> Ticket:
    return Ticket(
        id=ticket_id,
        reservation_id=uuid.uuid4(),
        event_id=event_id,
        ticket_type_id=uuid.uuid4(),
        owner_user_id=uuid.uuid4(),
        state=state,
    )


def _session(ticket: Ticket | None) -> MagicMock:
    session = MagicMock()

    async def _get(model: Any, key: Any) -> Any:
        del model
        if ticket is not None and ticket.id == key:
            return ticket
        return None

    session.get = AsyncMock(side_effect=_get)

    async def _execute(*_args: Any, **_kwargs: Any) -> Any:
        result = MagicMock()
        result.first.return_value = ({"id": ticket.id},) if ticket else None
        return result

    session.execute = AsyncMock(side_effect=_execute)
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    return session


def _audit() -> MagicMock:
    a = MagicMock(spec=AuditService)
    a.record = AsyncMock()
    return a


async def test_validate_happy_path_transitions_ticket(redis_client: Any) -> None:
    event_id = uuid.uuid4()
    venue_id = uuid.uuid4()
    ticket = _ticket(ticket_id=uuid.uuid4(), event_id=event_id)
    from tests.v1.conftest import register_test_tickets

    register_test_tickets(ticket)
    session = _session(ticket)
    token = _mint_ticket_jwt(ticket_id=ticket.id, event_id=event_id, venue_id=venue_id)
    audit = _audit()
    outcome = await validate_entry(
        session,
        redis_client,
        ticket_jwt=token,
        scanner=_scanner(venue_id),
        scanner_event_id=event_id,
        scanner_venue_id=venue_id,
        audit=audit,
    )
    assert outcome.allowed is True
    assert outcome.ticket_id == ticket.id
    actions = {c.kwargs["action"] for c in audit.record.await_args_list}
    assert AuditAction.ENTRY_VALIDATED in actions


async def test_validate_rejects_bad_signature(redis_client: Any) -> None:
    audit = _audit()
    outcome = await validate_entry(
        _session(None),
        redis_client,
        ticket_jwt="not.a.valid.jwt",
        scanner=_scanner(uuid.uuid4()),
        scanner_event_id=uuid.uuid4(),
        scanner_venue_id=uuid.uuid4(),
        audit=audit,
    )
    assert outcome.allowed is False
    assert outcome.reason == EntryReason.signature
    actions = {c.kwargs["action"] for c in audit.record.await_args_list}
    assert AuditAction.ENTRY_REJECTED in actions


async def test_validate_rejects_wrong_audience(redis_client: Any) -> None:
    event_id = uuid.uuid4()
    venue_id = uuid.uuid4()
    token = _mint_ticket_jwt(
        ticket_id=uuid.uuid4(),
        event_id=event_id,
        venue_id=venue_id,
        aud="qrew.something_else",
    )
    outcome = await validate_entry(
        _session(None),
        redis_client,
        ticket_jwt=token,
        scanner=_scanner(venue_id),
        scanner_event_id=event_id,
        scanner_venue_id=venue_id,
        audit=_audit(),
    )
    assert outcome.reason == EntryReason.audience


async def test_validate_rejects_expired_token(redis_client: Any) -> None:
    event_id = uuid.uuid4()
    venue_id = uuid.uuid4()
    token = _mint_ticket_jwt(
        ticket_id=uuid.uuid4(),
        event_id=event_id,
        venue_id=venue_id,
        expired=True,
    )
    outcome = await validate_entry(
        _session(None),
        redis_client,
        ticket_jwt=token,
        scanner=_scanner(venue_id),
        scanner_event_id=event_id,
        scanner_venue_id=venue_id,
        audit=_audit(),
    )
    assert outcome.reason == EntryReason.expired


async def test_validate_rejects_wrong_event_for_scanner(redis_client: Any) -> None:
    event_id = uuid.uuid4()
    venue_id = uuid.uuid4()
    token = _mint_ticket_jwt(
        ticket_id=uuid.uuid4(), event_id=event_id, venue_id=venue_id
    )
    outcome = await validate_entry(
        _session(None),
        redis_client,
        ticket_jwt=token,
        scanner=_scanner(venue_id),
        scanner_event_id=uuid.uuid4(),
        scanner_venue_id=venue_id,
        audit=_audit(),
    )
    assert outcome.reason == EntryReason.wrong_event


async def test_validate_rejects_replay(redis_client: Any) -> None:
    event_id = uuid.uuid4()
    venue_id = uuid.uuid4()
    ticket = _ticket(ticket_id=uuid.uuid4(), event_id=event_id)
    from tests.v1.conftest import register_test_tickets

    register_test_tickets(ticket)
    token = _mint_ticket_jwt(
        ticket_id=ticket.id, event_id=event_id, venue_id=venue_id, jti="fixed"
    )
    first = await validate_entry(
        _session(ticket),
        redis_client,
        ticket_jwt=token,
        scanner=_scanner(venue_id),
        scanner_event_id=event_id,
        scanner_venue_id=venue_id,
        audit=_audit(),
    )
    assert first.allowed is True
    second = await validate_entry(
        _session(ticket),
        redis_client,
        ticket_jwt=token,
        scanner=_scanner(venue_id),
        scanner_event_id=event_id,
        scanner_venue_id=venue_id,
        audit=_audit(),
    )
    assert second.reason == EntryReason.replay


async def test_validate_rejects_already_used_ticket(redis_client: Any) -> None:
    event_id = uuid.uuid4()
    venue_id = uuid.uuid4()
    ticket = _ticket(ticket_id=uuid.uuid4(), event_id=event_id, state=TicketState.used)
    token = _mint_ticket_jwt(ticket_id=ticket.id, event_id=event_id, venue_id=venue_id)
    outcome = await validate_entry(
        _session(ticket),
        redis_client,
        ticket_jwt=token,
        scanner=_scanner(venue_id),
        scanner_event_id=event_id,
        scanner_venue_id=venue_id,
        audit=_audit(),
    )
    assert outcome.reason == EntryReason.state


async def test_validate_rejects_not_found(redis_client: Any) -> None:
    event_id = uuid.uuid4()
    venue_id = uuid.uuid4()
    token = _mint_ticket_jwt(
        ticket_id=uuid.uuid4(), event_id=event_id, venue_id=venue_id
    )
    outcome = await validate_entry(
        _session(None),
        redis_client,
        ticket_jwt=token,
        scanner=_scanner(venue_id),
        scanner_event_id=event_id,
        scanner_venue_id=venue_id,
        audit=_audit(),
    )
    assert outcome.reason == EntryReason.not_found


def test_jwt_exports_are_present() -> None:
    # cover the import surface used by validate_entry
    assert jwt.ExpiredSignatureError
    assert jwt.InvalidTokenError
