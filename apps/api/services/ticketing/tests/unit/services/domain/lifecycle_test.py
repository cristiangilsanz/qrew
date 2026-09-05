# tests which ticket state changes the lifecycle allows and how it applies them
import uuid

import pytest
from sqlalchemy.exc import DBAPIError

from com.qode.qrew.v1.ticketing.models.ticket import Ticket, TicketState
from com.qode.qrew.v1.ticketing.services.domain.tickets.lifecycle import (
    TicketBusyError,
    TicketNotFoundError,
    TicketTransitionError,
    is_legal_transition,
    transition_ticket,
)

LEGAL = [
    (TicketState.reserved, TicketState.issued),
    (TicketState.reserved, TicketState.cancelled),
    (TicketState.reserved, TicketState.expired),
    (TicketState.issued, TicketState.scanning),
    (TicketState.issued, TicketState.on_sale),
    (TicketState.issued, TicketState.flagged),
    (TicketState.scanning, TicketState.redeemed),
    (TicketState.scanning, TicketState.issued),
    (TicketState.on_sale, TicketState.issued),
    (TicketState.flagged, TicketState.issued),
]

ILLEGAL = [
    (TicketState.reserved, TicketState.redeemed),
    (TicketState.issued, TicketState.redeemed),
    (TicketState.redeemed, TicketState.issued),
    (TicketState.cancelled, TicketState.issued),
    (TicketState.expired, TicketState.issued),
    (TicketState.scanning, TicketState.on_sale),
]


# verifies that every advertised transition is accepted
@pytest.mark.parametrize(("from_state", "to_state"), LEGAL)
def test_allows_a_legal_transition(from_state: TicketState, to_state: TicketState) -> None:
    assert is_legal_transition(from_state=from_state, to_state=to_state) is True


# verifies that a state cannot be skipped or reopened once final
@pytest.mark.parametrize(("from_state", "to_state"), ILLEGAL)
def test_refuses_an_illegal_transition(from_state: TicketState, to_state: TicketState) -> None:
    assert is_legal_transition(from_state=from_state, to_state=to_state) is False


# verifies that an abandoned scan can always be shown again
def test_allows_returning_an_abandoned_scan_to_issued() -> None:
    assert is_legal_transition(from_state=TicketState.scanning, to_state=TicketState.issued) is True


class _Result:
    # stores the row the lock query reports
    def __init__(self, row: object) -> None:
        self._row = row

    # returns the row the lock query found
    def first(self) -> object:
        return self._row


class _Session:
    # stores the ticket the session hands back and whether the lock succeeds
    def __init__(self, ticket: object, *, locked: bool = False, missing: bool = False) -> None:
        self._ticket = ticket
        self._locked = locked
        self._missing = missing
        self.flushed = False
        self.recorded: list[object] = []

    # collects whatever the transition leaves in the outbox
    def add(self, row: object) -> None:
        self.recorded.append(row)

    # stands in for the row lock query
    async def execute(self, *args: object, **kwargs: object) -> _Result:
        del args, kwargs
        if self._locked:
            raise DBAPIError("stmt", {}, Exception("locked"))
        return _Result(None if self._missing else ("row",))

    # returns the ticket the session was built with
    async def get(self, model: object, ticket_id: object) -> object:
        del model, ticket_id
        return self._ticket

    # records that the change was flushed
    async def flush(self) -> None:
        self.flushed = True


class _Audit:
    # collects every audit record written
    def __init__(self) -> None:
        self.records: list[dict[str, object]] = []

    # stores one audit record
    async def record(self, **kwargs: object) -> None:
        self.records.append(kwargs)


# builds a ticket in the given state
def _ticket(state: TicketState) -> Ticket:
    return Ticket(
        id=uuid.uuid4(),
        reservation_id=uuid.uuid4(),
        event_id=uuid.uuid4(),
        ticket_type_id=uuid.uuid4(),
        owner_user_id=uuid.uuid4(),
        state=state,
    )


class TestTransitionTicket:
    # verifies that a legal transition is applied and recorded
    async def test_applies_a_legal_transition(self) -> None:
        ticket = _ticket(TicketState.reserved)
        session, audit = _Session(ticket), _Audit()
        result = await transition_ticket(
            session,  # type: ignore[arg-type]
            ticket_id=ticket.id,
            to_state=TicketState.issued,
            reason="paid",
            actor_id=uuid.uuid4(),
            audit=audit,  # type: ignore[arg-type]
        )
        assert result.state is TicketState.issued
        assert result.issued_at is not None
        assert session.flushed is True
        assert audit.records[0]["action"] == "TICKET_STATE_CHANGED"

    # verifies that expiring a ticket stamps when it happened
    async def test_expiring_stamps_the_moment(self) -> None:
        ticket = _ticket(TicketState.reserved)
        result = await transition_ticket(
            _Session(ticket),  # type: ignore[arg-type]
            ticket_id=ticket.id,
            to_state=TicketState.expired,
            reason="unpaid",
            actor_id=uuid.uuid4(),
            audit=_Audit(),  # type: ignore[arg-type]
        )
        assert result.expired_at is not None

    # verifies that asking for the state a ticket already holds changes nothing
    async def test_a_repeated_transition_is_a_no_op(self) -> None:
        ticket = _ticket(TicketState.issued)
        session = _Session(ticket)
        result = await transition_ticket(
            session,  # type: ignore[arg-type]
            ticket_id=ticket.id,
            to_state=TicketState.issued,
            reason="again",
            actor_id=uuid.uuid4(),
            audit=_Audit(),  # type: ignore[arg-type]
        )
        assert result is ticket
        assert session.flushed is False

    # verifies that a ticket already locked by another caller is refused
    async def test_a_locked_ticket_is_refused(self) -> None:
        ticket = _ticket(TicketState.issued)
        with pytest.raises(TicketBusyError):
            await transition_ticket(
                _Session(ticket, locked=True),  # type: ignore[arg-type]
                ticket_id=ticket.id,
                to_state=TicketState.scanning,
                reason="scan",
                actor_id=uuid.uuid4(),
            )

    # verifies that an unknown ticket is reported as missing
    async def test_an_unknown_ticket_is_reported_missing(self) -> None:
        with pytest.raises(TicketNotFoundError):
            await transition_ticket(
                _Session(None, missing=True),  # type: ignore[arg-type]
                ticket_id=uuid.uuid4(),
                to_state=TicketState.issued,
                reason="paid",
                actor_id=uuid.uuid4(),
            )

    # verifies that a ticket in a final state cannot move again
    async def test_a_terminal_ticket_cannot_move(self) -> None:
        ticket = _ticket(TicketState.redeemed)
        with pytest.raises(TicketTransitionError):
            await transition_ticket(
                _Session(ticket),  # type: ignore[arg-type]
                ticket_id=ticket.id,
                to_state=TicketState.issued,
                reason="undo",
                actor_id=uuid.uuid4(),
            )

    # verifies that an illegal transition is refused
    async def test_an_illegal_transition_is_refused(self) -> None:
        ticket = _ticket(TicketState.reserved)
        with pytest.raises(TicketTransitionError):
            await transition_ticket(
                _Session(ticket),  # type: ignore[arg-type]
                ticket_id=ticket.id,
                to_state=TicketState.redeemed,
                reason="skip",
                actor_id=uuid.uuid4(),
            )

    # verifies that a failing audit writer does not undo the transition
    async def test_a_failing_audit_writer_does_not_undo_the_change(self) -> None:
        class _BrokenAudit:
            # raises so the caller has to survive a broken audit trail
            async def record(self, **kwargs: object) -> None:
                del kwargs
                raise RuntimeError("audit down")

        ticket = _ticket(TicketState.reserved)
        result = await transition_ticket(
            _Session(ticket),  # type: ignore[arg-type]
            ticket_id=ticket.id,
            to_state=TicketState.issued,
            reason="paid",
            actor_id=uuid.uuid4(),
            audit=_BrokenAudit(),  # type: ignore[arg-type]
        )
        assert result.state is TicketState.issued
