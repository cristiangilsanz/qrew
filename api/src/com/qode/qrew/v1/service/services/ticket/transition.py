import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.service.core.infra.errors import DomainError
from com.qode.qrew.v1.service.core.observability import traced
from com.qode.qrew.v1.service.models.audit.audit import AuditAction
from com.qode.qrew.v1.service.models.ticket import Ticket, TicketState
from com.qode.qrew.v1.service.services.audit import AuditService

logger = structlog.get_logger(__name__)


class TicketNotFoundError(DomainError):
    """Raised when a ticket id does not resolve."""


class TicketBusyError(DomainError):
    """Raised when another transaction holds the ticket row."""


class TicketTransitionError(DomainError):
    """Raised when a state transition is illegal."""


_TERMINAL: frozenset[TicketState] = frozenset({TicketState.used, TicketState.cancelled})

_LEGAL_TRANSITIONS: dict[TicketState, frozenset[TicketState]] = {
    TicketState.reserved: frozenset({TicketState.issued, TicketState.cancelled}),
    TicketState.issued: frozenset(
        {
            TicketState.entry_pending,
            TicketState.cancelled,
            TicketState.frozen,
            TicketState.flagged,
        }
    ),
    TicketState.frozen: frozenset(
        {TicketState.issued, TicketState.cancelled, TicketState.flagged}
    ),
    TicketState.entry_pending: frozenset(
        {TicketState.used, TicketState.issued, TicketState.cancelled}
    ),
    TicketState.flagged: frozenset({TicketState.cancelled, TicketState.issued}),
    TicketState.used: frozenset(),
    TicketState.cancelled: frozenset(),
}


def is_legal_transition(*, from_state: TicketState, to_state: TicketState) -> bool:
    """Return whether `from_state -> to_state` is in the FSM table."""
    return to_state in _LEGAL_TRANSITIONS.get(from_state, frozenset())


@traced("ticket.transition")
async def transition_ticket(
    session: AsyncSession,
    *,
    ticket_id: uuid.UUID,
    to_state: TicketState,
    reason: str,
    actor_id: uuid.UUID,
    audit: AuditService | None = None,
) -> Ticket:
    """Move a ticket to `to_state`, guarded by lock + legal-transition table."""
    try:
        result = await session.execute(
            text("SELECT id FROM tickets WHERE id = :id FOR UPDATE NOWAIT").bindparams(
                id=ticket_id
            )
        )
    except DBAPIError as exc:
        raise TicketBusyError(
            "Ticket is being updated by another caller", field="ticket_id"
        ) from exc
    if result.first() is None:
        raise TicketNotFoundError("Ticket not found", field="ticket_id")
    ticket = await session.get(Ticket, ticket_id)
    if ticket is None:
        raise TicketNotFoundError("Ticket not found", field="ticket_id")
    if ticket.state == to_state:
        return ticket
    if ticket.state in _TERMINAL:
        raise TicketTransitionError(
            f"Ticket is in terminal state {ticket.state}", field="state"
        )
    if not is_legal_transition(from_state=ticket.state, to_state=to_state):
        raise TicketTransitionError(
            f"Illegal transition {ticket.state} -> {to_state}", field="state"
        )
    previous_state = ticket.state
    ticket.state = to_state
    ticket.state_updated_at = datetime.now(timezone.utc)
    await session.flush()
    writer = audit or AuditService()
    payload: dict[str, Any] = {
        "from": previous_state.value,
        "to": to_state.value,
        "reason": reason,
    }
    try:
        await writer.record(
            action=AuditAction.TICKET_STATE_CHANGED,
            actor_id=actor_id,
            entity_type="ticket",
            entity_id=str(ticket.id),
            payload=payload,
        )
    except Exception:
        await logger.awarning(
            "audit_write_failed", action=AuditAction.TICKET_STATE_CHANGED
        )
    return ticket
