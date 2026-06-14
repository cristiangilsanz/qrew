from fastapi import APIRouter

from com.qode.qrew.v1.catalog.routers.event import router as events_router
from com.qode.qrew.v1.catalog.routers.organisation import router as organisations_router
from com.qode.qrew.v1.catalog.routers.page import Page, clamp_limit
from com.qode.qrew.v1.catalog.routers.pagination import cursor_paginate
from com.qode.qrew.v1.catalog.routers.public_catalog import router as public_catalog_router
from com.qode.qrew.v1.catalog.routers.search import router as search_router
from com.qode.qrew.v1.catalog.routers.ticket_type import router as ticket_types_router
from com.qode.qrew.v1.catalog.routers.venue import router as venues_router

__all__ = ["Page", "clamp_limit", "cursor_paginate", "router"]

router = APIRouter(prefix="/v1")
router.include_router(organisations_router)
router.include_router(venues_router)
router.include_router(events_router)
router.include_router(ticket_types_router)
router.include_router(public_catalog_router)
router.include_router(search_router)
