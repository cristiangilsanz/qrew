from fastapi import HTTPException

from com.qode.qrew.v1.identity.core.registration.captcha import (
    CaptchaService,
    build_captcha_service,
)
from com.qode.qrew.v1.identity.services.infra.geoip import GeoIpService
from com.qode.qrew.v1.identity.services.infra.notification import (
    NotificationDispatcher,
    build_notification_dispatcher,
)
from com.qode.qrew.v1.identity.services.kyc.ocr import OcrService
from com.qode.qrew.v1.identity.settings import settings


def get_captcha_service() -> CaptchaService:
    """Build the captcha service."""
    return build_captcha_service()


def get_notification_service() -> NotificationDispatcher:
    """Build the notification dispatcher."""
    return build_notification_dispatcher()


def get_geoip_service() -> GeoIpService:
    """Build the GeoIP service."""
    return GeoIpService(settings.geoip_db_path)


def get_ocr_service() -> OcrService:
    """Build the OCR service."""
    return OcrService()


def domain_error(message: str, field: str | None, http_status: int) -> HTTPException:
    """Convert a business-rule error to an HTTP exception."""
    return HTTPException(status_code=http_status, detail={"message": message, "field": field})
