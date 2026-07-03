from fastapi import APIRouter

from .audit import router as audit_router

router = APIRouter(prefix="/v1")
router.include_router(audit_router)
