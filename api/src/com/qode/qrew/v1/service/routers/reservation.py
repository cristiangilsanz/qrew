import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.service.core.auth.auth import get_current_user
from com.qode.qrew.v1.service.core.idempotency import idempotent
from com.qode.qrew.v1.service.core.infra.database import get_db
from com.qode.qrew.v1.service.core.infra.limiter import limiter
from com.qode.qrew.v1.service.core.locking.errors import LockUnavailableError
from com.qode.qrew.v1.service.models.auth.user import User
from com.qode.qrew.v1.service.models.reservation import Reservation
from com.qode.qrew.v1.service.models.ticket import Ticket
from com.qode.qrew.v1.service.repositories.event import EventRepository
from com.qode.qrew.v1.service.repositories.reservation import ReservationRepository
from com.qode.qrew.v1.service.repositories.ticket_type import TicketTypeRepository
from com.qode.qrew.v1.service.schemas.reservation import (
    ReservationCreateRequest,
    ReservationResponse,
    ReservationTicketItem,
)
from com.qode.qrew.v1.service.services.audit import AuditService
from com.qode.qrew.v1.service.services.reservation import (
    ReservationError,
    ReservationService,
    TierBusyError,
)

router = APIRouter(tags=["reservations"])


def _service(db: AsyncSession) -> ReservationService:
    return ReservationService(
        db,
        ReservationRepository(db),
        EventRepository(db),
        TicketTypeRepository(db),
        AuditService(),
    )


def _to_response(
    reservation: Reservation, tickets: list[Ticket]
) -> ReservationResponse:
    return ReservationResponse(
        id=reservation.id,
        event_id=reservation.event_id,
        ticket_type_id=reservation.ticket_type_id,
        quantity=reservation.quantity,
        status=reservation.status,
        expires_at=reservation.expires_at,
        created_at=reservation.created_at,
        tickets=[
            ReservationTicketItem(id=ticket.id, state=ticket.state)
            for ticket in tickets
        ],
    )


def _bad_request(error: ReservationError) -> HTTPException:
    code = (
        status.HTTP_404_NOT_FOUND
        if error.field in {"event_id", "reservation_id", "ticket_type_id"}
        else status.HTTP_409_CONFLICT
        if error.field == "quantity"
        else status.HTTP_400_BAD_REQUEST
    )
    return HTTPException(
        status_code=code,
        detail={"message": error.message, "field": error.field},
    )


@router.post(
    "/events/{event_id}/reserve",
    response_model=ReservationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Reserve tickets against an event under the per-user limit",
)
@limiter.limit("30/minute")  # type: ignore[misc]
@idempotent(scope="user", ttl_seconds=300)
async def reserve_event(
    request: Request,
    event_id: uuid.UUID,
    body: ReservationCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReservationResponse:
    """Atomic capacity-guarded reservation against an event tier."""
    del request
    try:
        reservation = await _service(db).reserve(
            user_id=current_user.id,
            event_id=event_id,
            ticket_type_id=body.ticket_type_id,
            quantity=body.quantity,
        )
    except ReservationError as exc:
        raise _bad_request(exc) from exc
    except TierBusyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Ticket type is being purchased by another caller",
                "field": "ticket_type_id",
            },
        ) from exc
    except LockUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Another reservation by this user is in progress",
                "field": None,
            },
        ) from exc
    tickets = await ReservationRepository(db).list_tickets(reservation.id)
    return _to_response(reservation, tickets)


@router.post(
    "/reservations/{reservation_id}/cancel",
    response_model=ReservationResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel an open reservation",
)
@limiter.limit("30/minute")  # type: ignore[misc]
@idempotent(scope="user", ttl_seconds=300)
async def cancel_reservation(
    request: Request,
    reservation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReservationResponse:
    """Cancel a reservation the caller owns; frees the reserved capacity."""
    del request
    try:
        reservation = await _service(db).cancel(
            actor_id=current_user.id, reservation_id=reservation_id
        )
    except ReservationError as exc:
        raise _bad_request(exc) from exc
    except LockUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Another lifecycle change is in progress",
                "field": None,
            },
        ) from exc
    tickets = await ReservationRepository(db).list_tickets(reservation.id)
    return _to_response(reservation, tickets)


@router.get(
    "/reservations/{reservation_id}",
    response_model=ReservationResponse,
    status_code=status.HTTP_200_OK,
    summary="Read a reservation owned by the caller",
)
@limiter.limit("60/minute")  # type: ignore[misc]
async def get_reservation(
    request: Request,
    reservation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReservationResponse:
    """Return the reservation including its tickets and countdown."""
    del request
    try:
        reservation, tickets = await _service(db).get_for_user(
            actor_id=current_user.id, reservation_id=reservation_id
        )
    except ReservationError as exc:
        raise _bad_request(exc) from exc
    return _to_response(reservation, tickets)
