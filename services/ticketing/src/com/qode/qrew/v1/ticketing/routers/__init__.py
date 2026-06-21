from fastapi import APIRouter

from com.qode.qrew.v1.ticketing.routers.admission import router as admission_router
from com.qode.qrew.v1.ticketing.routers.tickets.qr import router as ticket_qr_router
from com.qode.qrew.v1.ticketing.routers.tickets.restore import router as ticket_restore_router

router = APIRouter(prefix="/v1")
router.include_router(ticket_qr_router)
router.include_router(ticket_restore_router)
router.include_router(admission_router)
