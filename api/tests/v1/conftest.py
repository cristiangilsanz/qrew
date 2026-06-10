from collections.abc import Iterator
from typing import Any

import pytest

from com.qode.qrew.v1.service.models.ticket import Ticket

_REGISTRY: list[Ticket] = []


def register_test_tickets(*tickets: Ticket) -> None:
    """Register tickets so the unit-test stub for `transition_ticket` can mutate them."""
    _REGISTRY.extend(tickets)


@pytest.fixture(autouse=True)
def _stub_ticket_transition(  # pyright: ignore[reportUnusedFunction]
    request: pytest.FixtureRequest,
) -> Iterator[None]:
    """Replace the FSM helper with a direct mutator for unit tests."""
    _REGISTRY.clear()
    get_marker: Any = request.node.get_closest_marker  # type: ignore[reportUnknownMemberType]
    if get_marker("real_ticket_transition") is not None:
        yield
        return

    async def _stub(session: Any, **kwargs: Any) -> Ticket | None:
        del session
        from datetime import UTC, datetime

        ticket_id = kwargs["ticket_id"]
        to_state = kwargs["to_state"]
        for ticket in _REGISTRY:
            if ticket.id == ticket_id:
                ticket.state = to_state
                ticket.state_updated_at = datetime.now(UTC)
                return ticket
        return None

    import com.qode.qrew.v1.service.services.payment.payment as payment_mod
    import com.qode.qrew.v1.service.services.reservation.reservation as reservation_mod

    original_payment = payment_mod.transition_ticket
    original_reservation = reservation_mod.transition_ticket
    payment_mod.transition_ticket = _stub  # type: ignore[assignment]
    reservation_mod.transition_ticket = _stub  # type: ignore[assignment]
    try:
        yield
    finally:
        payment_mod.transition_ticket = original_payment
        reservation_mod.transition_ticket = original_reservation
        _REGISTRY.clear()
