from collections.abc import AsyncGenerator

import redis.asyncio as aioredis
from fastapi import Depends, Header, HTTPException, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.sales.core.config import settings
from com.qode.qrew.v1.sales.core.database import get_db
from com.qode.qrew.v1.sales.repositories.market import MarketRepository
from com.qode.qrew.v1.sales.repositories.projections import (
    EventContextRepository,
    TicketTypeInventoryRepository,
)
from com.qode.qrew.v1.sales.repositories.reservation import ReservationRepository
from com.qode.qrew.v1.sales.services.application.audit import AuditService
from com.qode.qrew.v1.sales.services.application.market.service import MarketService
from com.qode.qrew.v1.sales.services.application.queue.service import QueueService
from com.qode.qrew.v1.sales.services.application.reservation import ReservationService

limiter = Limiter(key_func=get_remote_address, enabled=settings.ratelimit_enabled)


async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:  # type: ignore[type-arg]
    client: aioredis.Redis = aioredis.from_url(  # type: ignore[type-arg]
        settings.redis_url, decode_responses=False
    )
    try:
        yield client
    finally:
        await client.aclose()


async def verify_internal_key(
    x_internal_key: str = Header(alias="X-Internal-Key", default=""),
) -> None:
    if not x_internal_key or x_internal_key != settings.internal_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


def get_reservation_service(db: AsyncSession = Depends(get_db)) -> ReservationService:
    return ReservationService(
        db,
        ReservationRepository(db),
        EventContextRepository(db),
        TicketTypeInventoryRepository(db),
        AuditService(),
    )


def get_queue_service(db: AsyncSession = Depends(get_db)) -> QueueService:
    return QueueService(EventContextRepository(db), AuditService())


def get_market_service(db: AsyncSession = Depends(get_db)) -> MarketService:
    return MarketService(
        MarketRepository(db),
        EventContextRepository(db),
        TicketTypeInventoryRepository(db),
        AuditService(),
        assignment_ttl_hours=settings.market_assignment_ttl_hours,
        listing_ttl_days=settings.market_listing_ttl_days,
    )
