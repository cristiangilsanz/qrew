from fastapi import APIRouter

from com.qode.qrew.v1.entry.routers.admin.scanners import (
    router as admin_scanners_router,
)
from com.qode.qrew.v1.entry.routers.entry import router as entry_router
from com.qode.qrew.v1.entry.routers.entry_stats import router as entry_stats_router
from com.qode.qrew.v1.entry.routers.scanner import router as scanner_router

router = APIRouter(prefix="/v1")
router.include_router(entry_router)
router.include_router(entry_stats_router)
router.include_router(scanner_router)
router.include_router(admin_scanners_router)
