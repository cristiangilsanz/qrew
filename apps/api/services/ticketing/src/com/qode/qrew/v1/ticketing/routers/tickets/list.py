import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.ticketing.core.database import get_db
from com.qode.qrew.v1.ticketing.core.dependencies import limiter
from com.qode.qrew.v1.ticketing.core.principals import AuthenticatedUser, get_current_user
from com.qode.qrew.v1.ticketing.repositories.ticket import TicketRepository
from com.qode.qrew.v1.ticketing.schemas.tickets.ticket import TicketResponse

router = APIRouter(prefix="/tickets", tags=["tickets"])


_QR_ELIGIBLE_STATES = {"issued", "scanning"}
_LIMIT_COUNTING_STATES = {"reserved", "issued", "scanning", "on_sale", "flagged"}


def _to_response(ticket: object) -> TicketResponse:
    from com.qode.qrew.v1.ticketing.models.ticket import Ticket

    t: Ticket = ticket  # type: ignore[assignment]
    state_val = t.state.value
    return TicketResponse(
        id=t.id,
        reservation_id=t.reservation_id,
        event_id=t.event_id,
        ticket_type_id=t.ticket_type_id,
        state=state_val,
        state_updated_at=t.state_updated_at,
        issued_at=t.issued_at,
        expired_at=t.expired_at,
        holder_name=t.holder_name,
        holder_dni=t.holder_dni,
        created_at=t.created_at,
        qr_eligible=state_val in _QR_ELIGIBLE_STATES,
        counts_toward_limit=state_val in _LIMIT_COUNTING_STATES,
    )


@router.get(
    "",
    response_model=list[TicketResponse],
    status_code=status.HTTP_200_OK,
    summary="List all tickets owned by the authenticated user",
)
@limiter.limit("60/minute")  # type: ignore[misc]
async def list_tickets(
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[TicketResponse]:
    del request
    tickets = await TicketRepository(db).list_by_user(current_user.id)
    return [_to_response(t) for t in tickets]


@router.get(
    "/{ticket_id}",
    response_model=TicketResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a single ticket owned by the authenticated user",
)
@limiter.limit("60/minute")  # type: ignore[misc]
async def get_ticket(
    request: Request,
    ticket_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TicketResponse:
    del request
    ticket = await TicketRepository(db).get_by_id(ticket_id)
    if ticket is None or ticket.owner_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail={"message": "Ticket not found"}
        )
    return _to_response(ticket)
