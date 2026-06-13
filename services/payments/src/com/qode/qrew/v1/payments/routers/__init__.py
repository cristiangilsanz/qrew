from fastapi import APIRouter

from com.qode.qrew.v1.payments.routers.payment import router as payment_router

router = APIRouter(prefix="/v1")
router.include_router(payment_router)
