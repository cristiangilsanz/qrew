# tests which ticket state changes the lifecycle allows
import pytest

from com.qode.qrew.v1.ticketing.models.ticket import TicketState
from com.qode.qrew.v1.ticketing.services.domain.tickets.lifecycle import is_legal_transition

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
