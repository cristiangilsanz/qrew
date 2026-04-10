from fastapi import APIRouter

from com.qode.qrew.v1.service.routers.auth import router as auth_router
from com.qode.qrew.v1.service.routers.health import router as health_router

router = APIRouter(prefix="/v1")
router.include_router(health_router)
router.include_router(auth_router)
