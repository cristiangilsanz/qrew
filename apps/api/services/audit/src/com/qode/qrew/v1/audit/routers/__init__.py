from fastapi import APIRouter

from .audit import router as audit_router
from .internal import router as internal_router

router = APIRouter(prefix="/v1")
router.include_router(audit_router)
router.include_router(internal_router)
