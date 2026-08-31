# tests the flags a ticket response derives from its state
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from com.qode.qrew.v1.ticketing.models.ticket import TicketState
from com.qode.qrew.v1.ticketing.routers.tickets.list import _to_response

NOW = datetime(2026, 6, 1, tzinfo=UTC)


# builds a stand in ticket row in the state under test
def _ticket(state: TicketState, **kwargs: object) -> SimpleNamespace:
    base = {
        "id": uuid.uuid4(),
        "reservation_id": uuid.uuid4(),
        "event_id": uuid.uuid4(),
        "ticket_type_id": uuid.uuid4(),
        "state": state,
        "state_updated_at": NOW,
        "issued_at": NOW,
        "expired_at": None,
        "holder_name": "Admin",
        "holder_document_type": "dni",
        "holder_dni": "00000001R",
        "created_at": NOW,
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


# verifies that only a live ticket may show a qr
@pytest.mark.parametrize(
    ("state", "eligible"),
    [
        (TicketState.issued, True),
        (TicketState.scanning, True),
        (TicketState.reserved, False),
        (TicketState.redeemed, False),
        (TicketState.cancelled, False),
        (TicketState.expired, False),
    ],
)
def test_reports_which_states_may_show_a_qr(state: TicketState, eligible: bool) -> None:
    assert _to_response(_ticket(state)).qr_eligible is eligible


# verifies that only a ticket still held counts toward the per user limit
@pytest.mark.parametrize(
    ("state", "counts"),
    [
        (TicketState.reserved, True),
        (TicketState.issued, True),
        (TicketState.scanning, True),
        (TicketState.on_sale, True),
        (TicketState.flagged, True),
        (TicketState.redeemed, False),
        (TicketState.cancelled, False),
        (TicketState.expired, False),
    ],
)
def test_reports_which_states_count_toward_the_limit(state: TicketState, counts: bool) -> None:
    assert _to_response(_ticket(state)).counts_toward_limit is counts


# verifies that the declared document type travels with the holder
def test_carries_the_holder_document_type() -> None:
    response = _to_response(
        _ticket(TicketState.issued, holder_document_type="other", holder_dni="AB123456")
    )
    assert response.holder_document_type == "other"
    assert response.holder_dni == "AB123456"


# verifies that a ticket with no holder named yet still renders
def test_renders_a_ticket_without_a_holder() -> None:
    response = _to_response(
        _ticket(
            TicketState.reserved,
            holder_name=None,
            holder_document_type=None,
            holder_dni=None,
        )
    )
    assert response.holder_name is None
    assert response.holder_document_type is None
