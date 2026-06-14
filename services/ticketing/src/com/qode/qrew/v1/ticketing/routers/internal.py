"""Internal API routes exposed only to other services within the same deployment."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.ticketing.database import get_db
from infra.locking import LockUnavailableError, redlock
from com.qode.qrew.v1.ticketing.models.ticket import TicketState
from com.qode.qrew.v1.ticketing.services.ticket.transition import (
    TicketTransitionError,
    transition_ticket,
)
from com.qode.qrew.v1.ticketing.settings import settings

router = APIRouter(prefix="/_internal", include_in_schema=False)


def _require_internal_key(request: Request) -> None:
    key = request.headers.get("X-Internal-Key", "")
    if not key or key != settings.internal_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
        )


class _UseBody(BaseModel):
    actor_id: uuid.UUID


@router.post("/tickets/{ticket_id}/use", status_code=status.HTTP_204_NO_CONTENT)
async def use_ticket(
    ticket_id: uuid.UUID,
    body: _UseBody,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Marks a ticket as used after validating entry at the gate."""
    _require_internal_key(request)
    try:
        async with redlock(f"ticket:{ticket_id}:entry", redis_url=settings.redis_url, ttl_seconds=10):
            await transition_ticket(
                db,
                ticket_id=ticket_id,
                to_state=TicketState.used,
                reason="entry_validated",
                actor_id=body.actor_id,
            )
    except LockUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "Ticket is busy", "field": "ticket_id"},
        ) from exc
    except TicketTransitionError as exc:
        if "terminal" in exc.message.lower() or "used" in exc.message.lower():
            return
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": exc.message, "field": exc.field},
        ) from exc
