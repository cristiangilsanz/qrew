import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.ticketing.services.audit import AuditService
from com.qode.qrew.v1.ticketing.services.auth.auth import AuthenticatedUser, get_current_user
from com.qode.qrew.v1.ticketing.database import get_db
from com.qode.qrew.v1.ticketing.services.infra.limiter import limiter
from com.qode.qrew.v1.ticketing.services.ticket.restore import (
    TicketRestoreError,
    restore_frozen_ticket,
)

router = APIRouter(tags=["ticket-restore"])


def _domain_to_http(error: TicketRestoreError) -> HTTPException:
    code = (
        status.HTTP_404_NOT_FOUND
        if error.field in {"ticket_id", "device_id"} and error.message.endswith("not found")
        else status.HTTP_403_FORBIDDEN
        if error.field in {"reassertion", "attestation"}
        else status.HTTP_409_CONFLICT
    )
    return HTTPException(
        status_code=code,
        detail={"message": error.message, "field": error.field},
    )


@router.post(
    "/tickets/{ticket_id}/restore",
    status_code=status.HTTP_200_OK,
    summary="Restore a frozen ticket onto a re-enrolled device",
)
@limiter.limit("5/600seconds")  # type: ignore[misc]
async def restore_ticket(
    request: Request,
    ticket_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Restores a frozen ticket to active use on a newly enrolled device."""
    del request
    try:
        ticket = await restore_frozen_ticket(
            db,
            actor_id=current_user.id,
            ticket_id=ticket_id,
            session_device_id=current_user.device_id,
            last_asserted_at=current_user.last_asserted_at,
            audit=AuditService(),
        )
    except TicketRestoreError as exc:
        raise _domain_to_http(exc) from exc
    return {"ticket_id": str(ticket.id), "state": ticket.state.value}
