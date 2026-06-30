from fastapi import APIRouter

from ._deps import (
    get_fingerprint_service,
    get_kyc_review_service,
    get_login_lockout_service,
)
from .fingerprints import router as fingerprints_router
from .kyc import router as kyc_router
from .outbox_dlq import router as outbox_dlq_router
from .users import router as users_router

router = APIRouter(prefix="/admin", tags=["admin"])
router.include_router(kyc_router)
router.include_router(fingerprints_router)
router.include_router(users_router)
router.include_router(outbox_dlq_router)

__all__ = [
    "get_fingerprint_service",
    "get_kyc_review_service",
    "get_login_lockout_service",
    "router",
]
