import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.sales.models.projections import (
    EventContext,
    FingerprintContext,
    TicketTypeInventory,
    UserAgeContext,
)


class EventContextRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_event_id(self, event_id: uuid.UUID) -> EventContext | None:
        return await self._session.get(EventContext, event_id)

    async def upsert(
        self,
        *,
        event_id: uuid.UUID,
        status: str,
        sale_starts_at: datetime | None = None,
        sale_ends_at: datetime | None = None,
        max_tickets_per_user: int = 10,
        queue_required: bool = False,
        queue_admit_rate_per_minute: int = 50,
    ) -> None:
        ctx = await self._session.get(EventContext, event_id)
        if ctx is None:
            ctx = EventContext(
                event_id=event_id,
                status=status,
                sale_starts_at=sale_starts_at,
                sale_ends_at=sale_ends_at,
                max_tickets_per_user=max_tickets_per_user,
                queue_required=queue_required,
                queue_admit_rate_per_minute=queue_admit_rate_per_minute,
            )
            self._session.add(ctx)
        else:
            ctx.status = status
            if sale_starts_at is not None:
                ctx.sale_starts_at = sale_starts_at
            if sale_ends_at is not None:
                ctx.sale_ends_at = sale_ends_at
            ctx.max_tickets_per_user = max_tickets_per_user
            ctx.queue_required = queue_required
            ctx.queue_admit_rate_per_minute = queue_admit_rate_per_minute
        ctx.updated_at = datetime.now(UTC)
        await self._session.flush()


class TicketTypeInventoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, ticket_type_id: uuid.UUID) -> TicketTypeInventory | None:
        return await self._session.get(TicketTypeInventory, ticket_type_id)

    async def upsert(
        self,
        *,
        ticket_type_id: uuid.UUID,
        event_id: uuid.UUID,
        capacity: int,
        price_cents: int = 0,
        currency: str = "EUR",
    ) -> None:
        inv = await self._session.get(TicketTypeInventory, ticket_type_id)
        if inv is None:
            inv = TicketTypeInventory(
                ticket_type_id=ticket_type_id,
                event_id=event_id,
                capacity=capacity,
                reserved_count=0,
                price_cents=price_cents,
                currency=currency,
            )
            self._session.add(inv)
        else:
            inv.capacity = capacity
            inv.price_cents = price_cents
            inv.currency = currency
        inv.updated_at = datetime.now(UTC)
        await self._session.flush()


class UserAgeContextRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_user_id(self, user_id: uuid.UUID) -> UserAgeContext | None:
        return await self._session.get(UserAgeContext, user_id)

    async def upsert(self, *, user_id: uuid.UUID, registered_at: datetime) -> None:
        ctx = await self._session.get(UserAgeContext, user_id)
        if ctx is None:
            ctx = UserAgeContext(user_id=user_id, registered_at=registered_at)
            self._session.add(ctx)
        else:
            ctx.registered_at = registered_at
        ctx.updated_at = datetime.now(UTC)
        await self._session.flush()


class FingerprintContextRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_hash(self, fingerprint_hash: str) -> FingerprintContext | None:
        return await self._session.get(FingerprintContext, fingerprint_hash)

    async def seen(self, *, fingerprint_hash: str, now: datetime) -> None:
        ctx = await self._session.get(FingerprintContext, fingerprint_hash)
        if ctx is None:
            ctx = FingerprintContext(
                fingerprint_hash=fingerprint_hash,
                distinct_user_count=1,
                last_seen_at=now,
            )
            self._session.add(ctx)
        else:
            ctx.distinct_user_count += 1
            ctx.last_seen_at = now
        ctx.updated_at = datetime.now(UTC)
        await self._session.flush()
