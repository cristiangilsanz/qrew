# reads and writes payment rows
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.payments.models.payment import Payment


class PaymentRepository:
    # stores the session the repository queries through
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # reads a payment by its identifier
    async def get_by_id(self, payment_id: uuid.UUID) -> Payment | None:
        result = await self._session.execute(select(Payment).where(Payment.id == payment_id))
        return result.scalar_one_or_none()

    # reads the payment tied to a reservation
    async def get_by_reservation_id(self, reservation_id: uuid.UUID) -> Payment | None:
        result = await self._session.execute(
            select(Payment).where(Payment.reservation_id == reservation_id)
        )
        return result.scalar_one_or_none()

    # reads the payment tied to a market assignment
    async def get_by_assignment_id(self, assignment_id: uuid.UUID) -> Payment | None:
        result = await self._session.execute(
            select(Payment).where(Payment.market_assignment_id == assignment_id)
        )
        return result.scalar_one_or_none()

    # reads the payment tied to a stripe payment intent
    async def get_by_intent_id(self, intent_id: str) -> Payment | None:
        result = await self._session.execute(
            select(Payment).where(Payment.provider_payment_intent_id == intent_id)
        )
        return result.scalar_one_or_none()

    # writes a new payment to the database
    async def insert(self, payment: Payment) -> Payment:
        self._session.add(payment)
        await self._session.flush()
        await self._session.refresh(payment)
        return payment

    # flushes pending changes to the database
    async def flush(self) -> None:
        await self._session.flush()
