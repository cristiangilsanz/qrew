import pytest

from com.qode.qrew.v1.service.models.ticket import TicketState
from com.qode.qrew.v1.service.services.ticket import is_legal_transition


@pytest.mark.parametrize(
    ("from_state", "to_state"),
    [
        (TicketState.reserved, TicketState.issued),
        (TicketState.reserved, TicketState.cancelled),
        (TicketState.issued, TicketState.entry_pending),
        (TicketState.issued, TicketState.cancelled),
        (TicketState.issued, TicketState.frozen),
        (TicketState.issued, TicketState.flagged),
        (TicketState.frozen, TicketState.issued),
        (TicketState.frozen, TicketState.cancelled),
        (TicketState.frozen, TicketState.flagged),
        (TicketState.entry_pending, TicketState.used),
        (TicketState.entry_pending, TicketState.issued),
        (TicketState.entry_pending, TicketState.cancelled),
        (TicketState.flagged, TicketState.cancelled),
        (TicketState.flagged, TicketState.issued),
    ],
)
def test_legal_transitions_are_allowed(
    from_state: TicketState, to_state: TicketState
) -> None:
    assert is_legal_transition(from_state=from_state, to_state=to_state)


@pytest.mark.parametrize(
    ("from_state", "to_state"),
    [
        (TicketState.reserved, TicketState.entry_pending),
        (TicketState.reserved, TicketState.used),
        (TicketState.reserved, TicketState.frozen),
        (TicketState.issued, TicketState.used),
        (TicketState.issued, TicketState.reserved),
        (TicketState.entry_pending, TicketState.frozen),
        (TicketState.frozen, TicketState.entry_pending),
        (TicketState.frozen, TicketState.used),
    ],
)
def test_illegal_transitions_are_rejected(
    from_state: TicketState, to_state: TicketState
) -> None:
    assert not is_legal_transition(from_state=from_state, to_state=to_state)


@pytest.mark.parametrize("terminal", [TicketState.used, TicketState.cancelled])
def test_terminal_states_have_no_outgoing_transitions(
    terminal: TicketState,
) -> None:
    for state in TicketState:
        assert not is_legal_transition(from_state=terminal, to_state=state)
