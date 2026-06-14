from fastapi import APIRouter

from com.qode.qrew.v1.ticketing.routers.internal import router as internal_router
from com.qode.qrew.v1.ticketing.routers.ticket_qr import router as ticket_qr_router
from com.qode.qrew.v1.ticketing.routers.ticket_restore import router as ticket_restore_router

router = APIRouter(prefix="/v1")
router.include_router(ticket_qr_router)
router.include_router(ticket_restore_router)
router.include_router(internal_router)
