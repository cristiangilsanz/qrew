import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from com.qode.qrew.v1.ticketing.models.ticket import TicketState
from com.qode.qrew.v1.ticketing.services.application.tickets.entry import (
    TicketBusyError,
    TicketNotFoundError,
    TicketTransitionError,
    use_ticket,
)

_PATCH_TRANSITION = (
    "com.qode.qrew.v1.ticketing.services.application.tickets.entry.transition_ticket"
)
_PATCH_REDLOCK = "com.qode.qrew.v1.ticketing.services.application.tickets.entry.redlock"


def _make_redlock() -> MagicMock:
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=None)
    cm.__aexit__ = AsyncMock(return_value=None)
    return cm


def _make_session() -> MagicMock:
    session = MagicMock()
    session.commit = AsyncMock()
    return session


class TestUseTicket:
    async def test_transitions_ticket_to_used(self) -> None:
        session = _make_session()
        ticket_id = uuid.uuid4()
        actor_id = uuid.uuid4()

        with (
            patch(_PATCH_REDLOCK, return_value=_make_redlock()),
            patch(_PATCH_TRANSITION, new=AsyncMock()) as mock_transition,
        ):
            await use_ticket(session, ticket_id=ticket_id, actor_id=actor_id)

        mock_transition.assert_awaited_once_with(
            session,
            ticket_id=ticket_id,
            to_state=TicketState.used,
            reason="entry_validated",
            actor_id=actor_id,
        )

    async def test_commits_after_transition(self) -> None:
        session = _make_session()

        with (
            patch(_PATCH_REDLOCK, return_value=_make_redlock()),
            patch(_PATCH_TRANSITION, new=AsyncMock()),
        ):
            await use_ticket(session, ticket_id=uuid.uuid4(), actor_id=uuid.uuid4())

        session.commit.assert_awaited_once()

    async def test_silently_ignores_already_used(self) -> None:
        session = _make_session()

        with (
            patch(_PATCH_REDLOCK, return_value=_make_redlock()),
            patch(
                _PATCH_TRANSITION,
                new=AsyncMock(side_effect=TicketTransitionError("terminal state", field="state")),
            ),
        ):
            await use_ticket(session, ticket_id=uuid.uuid4(), actor_id=uuid.uuid4())

        session.commit.assert_not_awaited()

    async def test_silently_ignores_used_in_message(self) -> None:
        session = _make_session()

        with (
            patch(_PATCH_REDLOCK, return_value=_make_redlock()),
            patch(
                _PATCH_TRANSITION,
                new=AsyncMock(side_effect=TicketTransitionError("already used", field="state")),
            ),
        ):
            await use_ticket(session, ticket_id=uuid.uuid4(), actor_id=uuid.uuid4())

        session.commit.assert_not_awaited()

    async def test_reraises_non_terminal_transition_error(self) -> None:
        session = _make_session()

        with (
            patch(_PATCH_REDLOCK, return_value=_make_redlock()),
            patch(
                _PATCH_TRANSITION,
                new=AsyncMock(
                    side_effect=TicketTransitionError(
                        "Illegal transition issued -> reserved", field="state"
                    )
                ),
            ),
            pytest.raises(TicketTransitionError),
        ):
            await use_ticket(session, ticket_id=uuid.uuid4(), actor_id=uuid.uuid4())

    async def test_propagates_not_found(self) -> None:
        session = _make_session()

        with (
            patch(_PATCH_REDLOCK, return_value=_make_redlock()),
            patch(
                _PATCH_TRANSITION,
                new=AsyncMock(side_effect=TicketNotFoundError("not found", field="ticket_id")),
            ),
            pytest.raises(TicketNotFoundError),
        ):
            await use_ticket(session, ticket_id=uuid.uuid4(), actor_id=uuid.uuid4())

    async def test_propagates_busy_error(self) -> None:
        session = _make_session()

        with (
            patch(_PATCH_REDLOCK, return_value=_make_redlock()),
            patch(
                _PATCH_TRANSITION,
                new=AsyncMock(side_effect=TicketBusyError("busy", field="ticket_id")),
            ),
            pytest.raises(TicketBusyError),
        ):
            await use_ticket(session, ticket_id=uuid.uuid4(), actor_id=uuid.uuid4())
