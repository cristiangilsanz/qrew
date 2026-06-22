import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.sales.models.reservation import ReservationStatus
from com.qode.qrew.v1.sales.repositories.projections import TicketTypeInventoryRepository
from com.qode.qrew.v1.sales.repositories.reservation import ReservationRepository


class PaymentContextError(Exception):
    def __init__(self, message: str, error_code: str) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code


@dataclass
class PaymentContext:
    amount_cents: int
    currency: str


async def get_payment_context(
    db: AsyncSession,
    *,
    reservation_id: uuid.UUID,
    user_id: uuid.UUID,
    default_currency: str,
) -> PaymentContext:
    reservation = await ReservationRepository(db).get_by_id(reservation_id)
    if reservation is None or reservation.user_id != user_id:
        raise PaymentContextError("Reservation not found", "not_found")
    if reservation.status != ReservationStatus.reserved:
        raise PaymentContextError("Reservation is not pending payment", "not_reserved")
    if reservation.expires_at <= datetime.now(UTC):
        raise PaymentContextError("Reservation has expired", "expired")
    inventory = await TicketTypeInventoryRepository(db).get_by_id(reservation.ticket_type_id)
    if inventory is None:
        raise PaymentContextError("Ticket type not found", "not_found")
    amount_cents = inventory.price_cents * reservation.quantity
    currency = inventory.currency or default_currency
    return PaymentContext(amount_cents=amount_cents, currency=currency)
