import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from com.qode.qrew.v1.service.models.auth.session import Session
from com.qode.qrew.v1.service.models.device.device import Device
from com.qode.qrew.v1.service.models.ticket import Ticket, TicketState
from com.qode.qrew.v1.service.services.ticket import (
    TicketRestoreError,
    restore_frozen_ticket,
)


def _now() -> datetime:
    return datetime.now(UTC)


def _ticket(
    *,
    owner: uuid.UUID,
    state: TicketState = TicketState.frozen,
    bound: uuid.UUID | None = None,
) -> Ticket:
    return Ticket(
        id=uuid.uuid4(),
        reservation_id=uuid.uuid4(),
        event_id=uuid.uuid4(),
        ticket_type_id=uuid.uuid4(),
        owner_user_id=owner,
        bound_device_id=bound,
        state=state,
    )


def _device(
    *,
    user_id: uuid.UUID,
    attested_minutes_ago: int = 30,
    revoked: bool = False,
) -> Device:
    now = _now()
    return Device(
        id=uuid.uuid4(),
        user_id=user_id,
        name="Phone",
        public_key=b"\x02" * 65,
        attested_at=now - timedelta(minutes=attested_minutes_ago),
        revoked_at=(now if revoked else None),
    )


def _session(
    *,
    user_id: uuid.UUID,
    device_id: uuid.UUID,
    asserted_seconds_ago: int = 10,
) -> Session:
    return Session(
        id=uuid.uuid4(),
        user_id=user_id,
        jti=uuid.uuid4().hex,
        device_id=device_id,
        last_asserted_at=_now() - timedelta(seconds=asserted_seconds_ago),
    )


def _db_with(*, ticket: Ticket | None, device: Device | None) -> MagicMock:
    db = MagicMock()

    async def _get(model: Any, key: Any) -> Any:
        if model is Ticket:
            return ticket if ticket and ticket.id == key else None
        if model is Device:
            return device if device and device.id == key else None
        return None

    db.get = AsyncMock(side_effect=_get)
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    return db


def _audit_stub() -> MagicMock:
    audit = MagicMock()
    audit.record = AsyncMock()
    return audit


async def test_restore_rejects_unowned_ticket() -> None:
    owner = uuid.uuid4()
    intruder = uuid.uuid4()
    ticket = _ticket(owner=owner)
    db = _db_with(ticket=ticket, device=None)
    with pytest.raises(TicketRestoreError, match="not found"):
        await restore_frozen_ticket(
            db,
            actor_id=intruder,
            ticket_id=ticket.id,
            auth_session=_session(user_id=intruder, device_id=uuid.uuid4()),
            audit=_audit_stub(),
        )


async def test_restore_rejects_non_frozen_ticket() -> None:
    owner = uuid.uuid4()
    ticket = _ticket(owner=owner, state=TicketState.issued)
    db = _db_with(ticket=ticket, device=None)
    with pytest.raises(TicketRestoreError, match="not frozen"):
        await restore_frozen_ticket(
            db,
            actor_id=owner,
            ticket_id=ticket.id,
            auth_session=_session(user_id=owner, device_id=uuid.uuid4()),
            audit=_audit_stub(),
        )


async def test_restore_rejects_same_device() -> None:
    owner = uuid.uuid4()
    device = _device(user_id=owner)
    ticket = _ticket(owner=owner, bound=device.id)
    db = _db_with(ticket=ticket, device=device)
    with pytest.raises(TicketRestoreError, match="new device"):
        await restore_frozen_ticket(
            db,
            actor_id=owner,
            ticket_id=ticket.id,
            auth_session=_session(user_id=owner, device_id=device.id),
            audit=_audit_stub(),
        )


async def test_restore_rejects_stale_reassertion() -> None:
    owner = uuid.uuid4()
    new_device = _device(user_id=owner)
    ticket = _ticket(owner=owner, bound=uuid.uuid4())
    db = _db_with(ticket=ticket, device=new_device)
    with pytest.raises(TicketRestoreError, match="reassertion"):
        await restore_frozen_ticket(
            db,
            actor_id=owner,
            ticket_id=ticket.id,
            auth_session=_session(
                user_id=owner, device_id=new_device.id, asserted_seconds_ago=600
            ),
            audit=_audit_stub(),
        )


async def test_restore_rejects_revoked_device() -> None:
    owner = uuid.uuid4()
    new_device = _device(user_id=owner, revoked=True)
    ticket = _ticket(owner=owner, bound=uuid.uuid4())
    db = _db_with(ticket=ticket, device=new_device)
    with pytest.raises(TicketRestoreError, match="revoked"):
        await restore_frozen_ticket(
            db,
            actor_id=owner,
            ticket_id=ticket.id,
            auth_session=_session(user_id=owner, device_id=new_device.id),
            audit=_audit_stub(),
        )


async def test_restore_rejects_stale_attestation() -> None:
    owner = uuid.uuid4()
    new_device = _device(user_id=owner, attested_minutes_ago=48 * 60)
    ticket = _ticket(owner=owner, bound=uuid.uuid4())
    db = _db_with(ticket=ticket, device=new_device)
    with pytest.raises(TicketRestoreError, match="attestation"):
        await restore_frozen_ticket(
            db,
            actor_id=owner,
            ticket_id=ticket.id,
            auth_session=_session(user_id=owner, device_id=new_device.id),
            audit=_audit_stub(),
        )


async def test_restore_happy_path_rotates_device_and_audits() -> None:
    owner = uuid.uuid4()
    new_device = _device(user_id=owner)
    previous_device = uuid.uuid4()
    ticket = _ticket(owner=owner, bound=previous_device)
    from tests.v1.conftest import register_test_tickets

    register_test_tickets(ticket)
    db = _db_with(ticket=ticket, device=new_device)
    audit = _audit_stub()
    result = await restore_frozen_ticket(
        db,
        actor_id=owner,
        ticket_id=ticket.id,
        auth_session=_session(user_id=owner, device_id=new_device.id),
        audit=audit,
    )
    assert result.state == TicketState.issued
    assert result.bound_device_id == new_device.id
    from com.qode.qrew.v1.service.models.audit.audit import AuditAction

    audited = {c.kwargs["action"] for c in audit.record.await_args_list}
    assert AuditAction.TICKET_RESTORED_AFTER_REENROL in audited
