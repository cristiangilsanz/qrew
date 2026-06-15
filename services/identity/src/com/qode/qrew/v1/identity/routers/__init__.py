from fastapi import APIRouter

from com.qode.qrew.v1.identity.routers.admin import router as admin_router
from com.qode.qrew.v1.identity.routers.auth import router as auth_router
from com.qode.qrew.v1.identity.routers.errors import default_responses, register_exception_handlers
from com.qode.qrew.v1.identity.routers.health import router as health_router
from com.qode.qrew.v1.identity.routers.page import Page, clamp_limit
from com.qode.qrew.v1.identity.routers.pagination import cursor_paginate
from com.qode.qrew.v1.identity.routers.probes import router as probes_router
from com.qode.qrew.v1.identity.routers.uploads import router as uploads_router
from com.qode.qrew.v1.identity.core.config import settings

router = APIRouter(prefix="/v1")
router.include_router(health_router)
router.include_router(auth_router)
router.include_router(admin_router)
router.include_router(uploads_router)

if settings.debug:
    from com.qode.qrew.v1.identity.routers.dev import router as dev_router

    router.include_router(dev_router)

__all__ = [
    "Page",
    "clamp_limit",
    "cursor_paginate",
    "default_responses",
    "probes_router",
    "register_exception_handlers",
    "router",
]
