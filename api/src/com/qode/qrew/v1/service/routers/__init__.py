from fastapi import APIRouter

from com.qode.qrew.v1.service.routers.admin import router as admin_router
from com.qode.qrew.v1.service.routers.auth import router as auth_router
from com.qode.qrew.v1.service.routers.health import router as health_router
from com.qode.qrew.v1.service.routers.uploads import router as uploads_router
from com.qode.qrew.v1.service.routers.queue import router as queue_router
from com.qode.qrew.v1.service.routers.ticket_qr import router as ticket_qr_router
from com.qode.qrew.v1.service.routers.ticket_restore import (
    router as ticket_restore_router,
)
from com.qode.qrew.v1.service.routers.reservation import (
    router as reservation_router,
)
from com.qode.qrew.v1.service.settings import settings

router = APIRouter(prefix="/v1")
router.include_router(health_router)
router.include_router(auth_router)
router.include_router(admin_router)
router.include_router(uploads_router)
router.include_router(reservation_router)
router.include_router(queue_router)
router.include_router(ticket_qr_router)
router.include_router(ticket_restore_router)

if settings.debug:
    from com.qode.qrew.v1.service.routers.dev import router as dev_router

    router.include_router(dev_router)
