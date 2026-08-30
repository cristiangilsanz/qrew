# tests restore
import uuid
from datetime import UTC, datetime, timedelta
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from com.qode.qrew.v1.ticketing.models.ticket import TicketState
from com.qode.qrew.v1.ticketing.services.application.audit import AuditService
from com.qode.qrew.v1.ticketing.services.application.tickets.restore import (
    TicketRestoreError,
    restore_on_sale_ticket,
)
from conftest import make_device, make_ticket

_PATCH_TRANSITION = (
    "com.qode.qrew.v1.ticketing.services.application.tickets.restore.transition_ticket"
)
_PATCH_SETTINGS = "com.qode.qrew.v1.ticketing.services.application.tickets.restore.settings"

_FAKE_SETTINGS = type(
    "S",
    (),
    {
        "ticket_qr_reassert_window_seconds": 30,
        "ticket_qr_attestation_max_age_hours": 24,
    },
)()


# provides fake settings
@pytest.fixture
def fake_settings() -> Generator[None, None, None]:
    with patch(_PATCH_SETTINGS, _FAKE_SETTINGS):
        yield


# a last_asserted_at value that is within the reassertion window right now
@pytest.fixture
def fresh_asserted_at() -> datetime:
    from datetime import datetime

    return datetime.now(UTC)


# handles make db
def _make_db(
    ticket: object = None,
    device: object = None,
) -> MagicMock:
    from com.qode.qrew.v1.ticketing.models.projections import DeviceContext
    from com.qode.qrew.v1.ticketing.models.ticket import Ticket

    # handles get
    async def _get(model: type, pk: object) -> object:
        if model is Ticket:
            return ticket
        if model is DeviceContext:
            return device
        return None

    db = MagicMock()
    db.get = _get
    db.flush = AsyncMock()
    return db


class TestRestoreFrozenTicket:
    # verifies that raises when ticket not found
    async def test_raises_when_ticket_not_found(
        self,
        fake_settings: None,
        user_id: uuid.UUID,
        device_id: uuid.UUID,
        audit: AuditService,
        now: datetime,
    ) -> None:
        db = _make_db(ticket=None, device=None)
        with pytest.raises(TicketRestoreError, match="not found"):
            await restore_on_sale_ticket(
                db,
                actor_id=user_id,
                ticket_id=uuid.uuid4(),
                session_device_id=device_id,
                last_asserted_at=now,
                audit=audit,
            )

    # verifies that raises when ticket owned by other
    async def test_raises_when_ticket_owned_by_other(
        self,
        fake_settings: None,
        user_id: uuid.UUID,
        device_id: uuid.UUID,
        audit: AuditService,
        now: datetime,
    ) -> None:
        ticket = make_ticket(owner_user_id=uuid.uuid4(), state=TicketState.on_sale)
        db = _make_db(ticket=ticket)
        with pytest.raises(TicketRestoreError, match="not found"):
            await restore_on_sale_ticket(
                db,
                actor_id=user_id,
                ticket_id=ticket.id,
                session_device_id=device_id,
                last_asserted_at=now,
                audit=audit,
            )

    # verifies that raises when ticket not frozen
    async def test_raises_when_ticket_not_frozen(
        self,
        fake_settings: None,
        user_id: uuid.UUID,
        device_id: uuid.UUID,
        audit: AuditService,
        now: datetime,
    ) -> None:
        ticket = make_ticket(owner_user_id=user_id, state=TicketState.issued)
        db = _make_db(ticket=ticket)
        with pytest.raises(TicketRestoreError, match="not on sale"):
            await restore_on_sale_ticket(
                db,
                actor_id=user_id,
                ticket_id=ticket.id,
                session_device_id=device_id,
                last_asserted_at=now,
                audit=audit,
            )

    # verifies that raises when no device in session
    async def test_raises_when_no_device_in_session(
        self,
        fake_settings: None,
        user_id: uuid.UUID,
        audit: AuditService,
        now: datetime,
    ) -> None:
        ticket = make_ticket(owner_user_id=user_id, state=TicketState.on_sale)
        db = _make_db(ticket=ticket)
        with pytest.raises(TicketRestoreError, match="device session"):
            await restore_on_sale_ticket(
                db,
                actor_id=user_id,
                ticket_id=ticket.id,
                session_device_id=None,
                last_asserted_at=now,
                audit=audit,
            )

    # verifies that raises when same device as bound
    async def test_raises_when_same_device_as_bound(
        self,
        fake_settings: None,
        user_id: uuid.UUID,
        device_id: uuid.UUID,
        audit: AuditService,
        now: datetime,
    ) -> None:
        ticket = make_ticket(
            owner_user_id=user_id, state=TicketState.on_sale, bound_device_id=device_id
        )
        db = _make_db(ticket=ticket)
        with pytest.raises(TicketRestoreError, match="enrolment required"):
            await restore_on_sale_ticket(
                db,
                actor_id=user_id,
                ticket_id=ticket.id,
                session_device_id=device_id,
                last_asserted_at=now,
                audit=audit,
            )

    # verifies that raises when no reassertion
    async def test_raises_when_no_reassertion(
        self,
        fake_settings: None,
        user_id: uuid.UUID,
        device_id: uuid.UUID,
        audit: AuditService,
    ) -> None:
        ticket = make_ticket(owner_user_id=user_id, state=TicketState.on_sale)
        db = _make_db(ticket=ticket)
        with pytest.raises(TicketRestoreError, match="reassertion"):
            await restore_on_sale_ticket(
                db,
                actor_id=user_id,
                ticket_id=ticket.id,
                session_device_id=device_id,
                last_asserted_at=None,
                audit=audit,
            )

    # verifies that raises when reassertion expired
    async def test_raises_when_reassertion_expired(
        self,
        fake_settings: None,
        user_id: uuid.UUID,
        device_id: uuid.UUID,
        audit: AuditService,
        now: datetime,
    ) -> None:
        stale = now - timedelta(seconds=60)
        ticket = make_ticket(owner_user_id=user_id, state=TicketState.on_sale)
        db = _make_db(ticket=ticket)
        with pytest.raises(TicketRestoreError, match="reassertion"):
            await restore_on_sale_ticket(
                db,
                actor_id=user_id,
                ticket_id=ticket.id,
                session_device_id=device_id,
                last_asserted_at=stale,
                audit=audit,
            )

    # verifies that raises when device not found
    async def test_raises_when_device_not_found(
        self,
        fake_settings: None,
        user_id: uuid.UUID,
        device_id: uuid.UUID,
        audit: AuditService,
        fresh_asserted_at: datetime,
    ) -> None:
        ticket = make_ticket(owner_user_id=user_id, state=TicketState.on_sale)
        db = _make_db(ticket=ticket, device=None)
        with pytest.raises(TicketRestoreError, match="Device not found."):
            await restore_on_sale_ticket(
                db,
                actor_id=user_id,
                ticket_id=ticket.id,
                session_device_id=device_id,
                last_asserted_at=fresh_asserted_at,
                audit=audit,
            )

    # verifies that raises when device owned by other
    async def test_raises_when_device_owned_by_other(
        self,
        fake_settings: None,
        user_id: uuid.UUID,
        device_id: uuid.UUID,
        audit: AuditService,
        fresh_asserted_at: datetime,
    ) -> None:
        ticket = make_ticket(owner_user_id=user_id, state=TicketState.on_sale)
        device = make_device(user_id=uuid.uuid4(), device_id=device_id)
        db = _make_db(ticket=ticket, device=device)
        with pytest.raises(TicketRestoreError, match="Device not found."):
            await restore_on_sale_ticket(
                db,
                actor_id=user_id,
                ticket_id=ticket.id,
                session_device_id=device_id,
                last_asserted_at=fresh_asserted_at,
                audit=audit,
            )

    # verifies that raises when device revoked
    async def test_raises_when_device_revoked(
        self,
        fake_settings: None,
        user_id: uuid.UUID,
        device_id: uuid.UUID,
        audit: AuditService,
        fresh_asserted_at: datetime,
    ) -> None:
        ticket = make_ticket(owner_user_id=user_id, state=TicketState.on_sale)
        device = make_device(user_id=user_id, device_id=device_id, revoked_at=fresh_asserted_at)
        db = _make_db(ticket=ticket, device=device)
        with pytest.raises(TicketRestoreError, match="revoked"):
            await restore_on_sale_ticket(
                db,
                actor_id=user_id,
                ticket_id=ticket.id,
                session_device_id=device_id,
                last_asserted_at=fresh_asserted_at,
                audit=audit,
            )

    # verifies that raises when device not attested
    async def test_raises_when_device_not_attested(
        self,
        fake_settings: None,
        user_id: uuid.UUID,
        device_id: uuid.UUID,
        audit: AuditService,
        fresh_asserted_at: datetime,
    ) -> None:
        ticket = make_ticket(owner_user_id=user_id, state=TicketState.on_sale)
        device = make_device(user_id=user_id, device_id=device_id, attested_at=None)
        db = _make_db(ticket=ticket, device=device)
        with pytest.raises(TicketRestoreError, match="attestation"):
            await restore_on_sale_ticket(
                db,
                actor_id=user_id,
                ticket_id=ticket.id,
                session_device_id=device_id,
                last_asserted_at=fresh_asserted_at,
                audit=audit,
            )

    # verifies that raises when attestation stale
    async def test_raises_when_attestation_stale(
        self,
        fake_settings: None,
        user_id: uuid.UUID,
        device_id: uuid.UUID,
        audit: AuditService,
        fresh_asserted_at: datetime,
    ) -> None:
        from datetime import datetime

        stale_attested = datetime.now(UTC) - timedelta(hours=25)
        ticket = make_ticket(owner_user_id=user_id, state=TicketState.on_sale)
        device = make_device(user_id=user_id, device_id=device_id, attested_at=stale_attested)
        db = _make_db(ticket=ticket, device=device)
        with pytest.raises(TicketRestoreError, match="attestation expired"):
            await restore_on_sale_ticket(
                db,
                actor_id=user_id,
                ticket_id=ticket.id,
                session_device_id=device_id,
                last_asserted_at=fresh_asserted_at,
                audit=audit,
            )

    # verifies that happy path transitions and rebinds
    async def test_happy_path_transitions_and_rebinds(
        self,
        fake_settings: None,
        user_id: uuid.UUID,
        device_id: uuid.UUID,
        audit: AuditService,
        fresh_asserted_at: datetime,
    ) -> None:
        ticket = make_ticket(owner_user_id=user_id, state=TicketState.on_sale)
        device = make_device(user_id=user_id, device_id=device_id)
        db = _make_db(ticket=ticket, device=device)

        with patch(_PATCH_TRANSITION, new=AsyncMock(return_value=ticket)):
            result = await restore_on_sale_ticket(
                db,
                actor_id=user_id,
                ticket_id=ticket.id,
                session_device_id=device_id,
                last_asserted_at=fresh_asserted_at,
                audit=audit,
            )

        assert result is ticket
        assert ticket.bound_device_id == device_id

    # verifies that audit failure does not raise
    async def test_audit_failure_does_not_raise(
        self,
        fake_settings: None,
        user_id: uuid.UUID,
        device_id: uuid.UUID,
        fresh_asserted_at: datetime,
    ) -> None:
        broken_audit = AsyncMock(spec=AuditService)
        broken_audit.record = AsyncMock(side_effect=RuntimeError("audit down"))
        ticket = make_ticket(owner_user_id=user_id, state=TicketState.on_sale)
        device = make_device(user_id=user_id, device_id=device_id)
        db = _make_db(ticket=ticket, device=device)

        with patch(_PATCH_TRANSITION, new=AsyncMock(return_value=ticket)):
            result = await restore_on_sale_ticket(
                db,
                actor_id=user_id,
                ticket_id=ticket.id,
                session_device_id=device_id,
                last_asserted_at=fresh_asserted_at,
                audit=broken_audit,
            )

        assert result is ticket
