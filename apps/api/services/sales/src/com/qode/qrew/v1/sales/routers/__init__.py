from fastapi import APIRouter

from com.qode.qrew.v1.sales.routers.billing import router as billing_router
from com.qode.qrew.v1.sales.routers.market import events_router as market_events_router
from com.qode.qrew.v1.sales.routers.market import market_router
from com.qode.qrew.v1.sales.routers.market import tickets_router as market_tickets_router
from com.qode.qrew.v1.sales.routers.queue import router as queue_router
from com.qode.qrew.v1.sales.routers.reservation import events_router as reservation_events_router
from com.qode.qrew.v1.sales.routers.reservation import router as reservation_router

v1_router = APIRouter(prefix="/v1")
v1_router.include_router(reservation_events_router)
v1_router.include_router(reservation_router)
v1_router.include_router(queue_router)
v1_router.include_router(billing_router)
v1_router.include_router(market_events_router)
v1_router.include_router(market_tickets_router)
v1_router.include_router(market_router)

__all__ = ["v1_router"]
