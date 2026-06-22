from fastapi import APIRouter

from com.qode.qrew.v1.catalog.routers.event import router as events_router
from com.qode.qrew.v1.catalog.routers.organisation import router as organisations_router
from com.qode.qrew.v1.catalog.core.utils.pagination import cursor_paginate
from com.qode.qrew.v1.catalog.routers.venue import router as venues_router
from pagination import Page, clamp_limit

__all__ = ["Page", "clamp_limit", "cursor_paginate", "router"]

router = APIRouter(prefix="/v1")
router.include_router(organisations_router)
router.include_router(venues_router)
router.include_router(events_router)
