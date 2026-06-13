"""Internal API routes consumed only by sibling services (gate, payments, etc.)."""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.service.core.infra.database import get_db
from com.qode.qrew.v1.service.core.locking import LockUnavailableError, redlock
from com.qode.qrew.v1.service.models.reservation import ReservationStatus
from com.qode.qrew.v1.service.models.ticket import TicketState
from com.qode.qrew.v1.service.repositories.reservation import ReservationRepository
from com.qode.qrew.v1.service.repositories.ticket_type import TicketTypeRepository
from com.qode.qrew.v1.service.services.ticket import (
    TicketTransitionError,
    transition_ticket,
)
from com.qode.qrew.v1.service.settings import settings

router = APIRouter(prefix="/internal", include_in_schema=False)


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
    """Transition a ticket to `used` state; called by the gate service."""
    _require_internal_key(request)
    try:
        async with redlock(f"ticket:{ticket_id}:entry", ttl_seconds=10):
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
            # Already used — idempotent
            return
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": exc.message, "field": exc.field},
        ) from exc


class _PaymentContextRequest(BaseModel):
    user_id: uuid.UUID


class _PaymentContextResponse(BaseModel):
    amount_cents: int
    currency: str


@router.post(
    "/reservations/{reservation_id}/payment-context",
    response_model=_PaymentContextResponse,
    status_code=status.HTTP_200_OK,
)
async def get_reservation_payment_context(
    reservation_id: uuid.UUID,
    body: _PaymentContextRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> _PaymentContextResponse:
    """Return amount+currency for a reservation; validates ownership and eligibility."""
    _require_internal_key(request)
    reservation = await ReservationRepository(db).get_by_id(reservation_id)
    if reservation is None or reservation.user_id != body.user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "not_found", "message": "Reservation not found"},
        )
    if reservation.status != ReservationStatus.reserved:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "not_reserved",
                "message": "Reservation is not pending payment",
            },
        )
    if reservation.expires_at <= datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={"error_code": "expired", "message": "Reservation has expired"},
        )
    tier = await TicketTypeRepository(db).get_by_id(reservation.ticket_type_id)
    if tier is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "not_found", "message": "Ticket type not found"},
        )
    amount_cents = tier.price_cents * reservation.quantity
    currency = tier.currency or settings.payments_default_currency
    return _PaymentContextResponse(amount_cents=amount_cents, currency=currency)
