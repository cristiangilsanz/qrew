from fastapi import APIRouter

from com.qode.qrew.v1.entry.routers.entry import entry_router, events_router
from com.qode.qrew.v1.entry.routers.health import router as health_router
from com.qode.qrew.v1.entry.routers.scanner import admin_router as admin_scanners_router
from com.qode.qrew.v1.entry.routers.scanner import router as scanners_router

router = APIRouter(prefix="/v1")
router.include_router(entry_router)
router.include_router(events_router)
router.include_router(scanners_router)
router.include_router(admin_scanners_router)
router.include_router(health_router)
