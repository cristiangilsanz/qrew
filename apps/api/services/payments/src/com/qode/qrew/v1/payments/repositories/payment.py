import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.payments.models.payment import Payment


class PaymentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, payment_id: uuid.UUID) -> Payment | None:
        result = await self._session.execute(select(Payment).where(Payment.id == payment_id))
        return result.scalar_one_or_none()

    async def get_by_reservation_id(self, reservation_id: uuid.UUID) -> Payment | None:
        result = await self._session.execute(
            select(Payment).where(Payment.reservation_id == reservation_id)
        )
        return result.scalar_one_or_none()

    async def get_by_intent_id(self, intent_id: str) -> Payment | None:
        result = await self._session.execute(
            select(Payment).where(Payment.provider_payment_intent_id == intent_id)
        )
        return result.scalar_one_or_none()

    async def insert(self, payment: Payment) -> Payment:
        self._session.add(payment)
        await self._session.flush()
        await self._session.refresh(payment)
        return payment

    async def flush(self) -> None:
        await self._session.flush()
