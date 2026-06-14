"""Internal API routes consumed only by sibling services (payments, etc.)."""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.sales.core.infra.database import get_db
from com.qode.qrew.v1.sales.models.reservation import Reservation, ReservationStatus
from com.qode.qrew.v1.sales.repositories.projections import TicketTypeInventoryRepository
from com.qode.qrew.v1.sales.repositories.reservation import ReservationRepository
from com.qode.qrew.v1.sales.settings import settings

router = APIRouter(prefix="/_internal", include_in_schema=False)


def _require_internal_key(request: Request) -> None:
    key = request.headers.get("X-Internal-Key", "")
    if not key or key != settings.internal_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
        )


class _PaymentContextRequest(BaseModel):
    user_id: uuid.UUID


class _PaymentContextResponse(BaseModel):
    amount_cents: int
    currency: str


@router.post(
    "/reservations/{reservation_id}/payment-context",
    response_model=_PaymentContextResponse,
)
async def get_reservation_payment_context(
    reservation_id: uuid.UUID,
    body: _PaymentContextRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> _PaymentContextResponse:
    """Return amount+currency for a reservation; called by the payments service."""
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
    inventory = await TicketTypeInventoryRepository(db).get_by_id(reservation.ticket_type_id)
    if inventory is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "not_found", "message": "Ticket type not found"},
        )
    amount_cents = inventory.price_cents * reservation.quantity
    currency = inventory.currency or settings.payments_default_currency
    return _PaymentContextResponse(amount_cents=amount_cents, currency=currency)
