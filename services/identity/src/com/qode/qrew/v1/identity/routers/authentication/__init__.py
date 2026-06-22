from fastapi import APIRouter

from ._deps import (
    get_deletion_service,
    get_complete_setup_service,
    get_device_attestation_service,
    get_device_binding_service,
    get_device_service,
    get_email_change_service,
    get_email_verification_service,
    get_fingerprint_service,
    get_kyc_service,
    get_login_service,
    get_logout_service,
    get_ocr_service,
    get_passkey_authentication_service,
    get_passkey_management_service,
    get_passkey_reassertion_service,
    get_passkey_registration_service,
    get_password_change_service,
    get_phone_change_service,
    get_phone_verification_service,
    get_recovery_service,
    get_refresh_service,
    get_registration_service,
    get_resend_email_verification_service,
    get_resend_phone_otp_service,
    get_session_service,
)
from .account import router as account_router
from .device import router as device_router
from .login import router as login_router
from .passkey import router as passkey_router
from .profile import router as profile_router
from .recovery import router as recovery_router
from .registration import router as registration_router
from .session import router as session_router
from .setup import router as setup_router

router = APIRouter(prefix="/auth", tags=["auth"])
router.include_router(registration_router)
router.include_router(login_router)
router.include_router(setup_router)
router.include_router(passkey_router)
router.include_router(session_router)
router.include_router(account_router)
router.include_router(device_router)
router.include_router(recovery_router)
router.include_router(profile_router)

__all__ = [
    "get_deletion_service",
    "get_complete_setup_service",
    "get_device_attestation_service",
    "get_device_binding_service",
    "get_device_service",
    "get_email_change_service",
    "get_email_verification_service",
    "get_fingerprint_service",
    "get_kyc_service",
    "get_login_service",
    "get_logout_service",
    "get_ocr_service",
    "get_passkey_authentication_service",
    "get_passkey_management_service",
    "get_passkey_reassertion_service",
    "get_passkey_registration_service",
    "get_password_change_service",
    "get_phone_change_service",
    "get_phone_verification_service",
    "get_recovery_service",
    "get_refresh_service",
    "get_registration_service",
    "get_resend_email_verification_service",
    "get_resend_phone_otp_service",
    "get_session_service",
    "router",
]
