from fastapi import APIRouter

from ._deps import (
    get_fingerprint_service,
    get_kyc_review_service,
    get_login_lockout_service,
    get_scanner_service,
)
from .audit import router as audit_router
from .fingerprints import router as fingerprints_router
from .kyc import router as kyc_router
from .scanners import router as scanners_router
from .users import router as users_router

router = APIRouter(prefix="/admin", tags=["admin"])
router.include_router(audit_router)
router.include_router(kyc_router)
router.include_router(fingerprints_router)
router.include_router(users_router)
router.include_router(scanners_router)

__all__ = [
    "get_fingerprint_service",
    "get_kyc_review_service",
    "get_login_lockout_service",
    "get_scanner_service",
    "router",
]
