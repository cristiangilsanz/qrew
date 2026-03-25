from fastapi import APIRouter

from com.qode.qrew.v1.service.routers.health import router as health_router

router = APIRouter(prefix="/v1")
router.include_router(health_router)
