import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.service.core.auth.auth import (
    get_current_session,
    get_current_user,
)
from com.qode.qrew.v1.service.core.infra.database import get_db
from com.qode.qrew.v1.service.core.infra.limiter import limiter
from com.qode.qrew.v1.service.models.auth.session import Session
from com.qode.qrew.v1.service.models.auth.user import User
from com.qode.qrew.v1.service.services.audit import AuditService
from com.qode.qrew.v1.service.services.ticket import (
    TicketRestoreError,
    restore_frozen_ticket,
)

router = APIRouter(tags=["ticket-restore"])


def _domain_to_http(error: TicketRestoreError) -> HTTPException:
    code = (
        status.HTTP_404_NOT_FOUND
        if error.field in {"ticket_id", "device_id"}
        and error.message.endswith("not found")
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
    current_user: User = Depends(get_current_user),
    auth_session: Session = Depends(get_current_session),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Transition `frozen → issued` on a different, attested, fresh-reasserted device."""
    del request
    try:
        ticket = await restore_frozen_ticket(
            db,
            actor_id=current_user.id,
            ticket_id=ticket_id,
            auth_session=auth_session,
            audit=AuditService(),
        )
    except TicketRestoreError as exc:
        raise _domain_to_http(exc) from exc
    return {"ticket_id": str(ticket.id), "state": ticket.state.value}
