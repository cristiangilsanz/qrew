from fastapi import APIRouter

from com.qode.qrew.v1.payments.routers.payment import router as payment_router
from com.qode.qrew.v1.payments.routers.payment import webhooks_router

router = APIRouter(prefix="/v1")
router.include_router(payment_router)
router.include_router(webhooks_router)
