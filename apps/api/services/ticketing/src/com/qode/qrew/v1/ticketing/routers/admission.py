import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.ticketing.core.database import get_db
from com.qode.qrew.v1.ticketing.core.dependencies import verify_internal_key
from com.qode.qrew.v1.ticketing.services.application.tickets.entry import (
    LockUnavailableError,
    TicketBusyError,
    TicketNotFoundError,
    TicketTransitionError,
    use_ticket,
)

router = APIRouter(
    prefix="/admission",
    include_in_schema=False,
    dependencies=[Depends(verify_internal_key)],
)


class _UseBody(BaseModel):
    actor_id: uuid.UUID


@router.post("/{ticket_id}/use", status_code=status.HTTP_204_NO_CONTENT)
async def mark_ticket_used(
    ticket_id: uuid.UUID,
    body: _UseBody,
    db: AsyncSession = Depends(get_db),
) -> None:
    try:
        await use_ticket(db, ticket_id=ticket_id, actor_id=body.actor_id)
    except LockUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "Ticket is busy", "field": "ticket_id"},
        ) from exc
    except TicketNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": exc.message, "field": exc.field},
        ) from exc
    except TicketBusyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": exc.message, "field": exc.field},
        ) from exc
    except TicketTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": exc.message, "field": exc.field},
        ) from exc
