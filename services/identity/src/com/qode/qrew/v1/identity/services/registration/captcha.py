from typing import Protocol

import httpx
import structlog

from com.qode.qrew.v1.identity.core.errors import DomainError
from com.qode.qrew.v1.identity.core.config import settings

logger = structlog.get_logger(__name__)


class CaptchaError(DomainError):
    """Raised when a captcha token cannot be verified."""


class CaptchaService(Protocol):
    async def verify(self, token: str, ip_address: str) -> None:
        """Verify a captcha token."""
        ...


class StubCaptchaService:
    """Captcha service that accepts all tokens without verification, for development use."""

    async def verify(self, token: str, ip_address: str) -> None:
        pass


class CloudflareTurnstileCaptchaService:
    """Captcha service backed by Cloudflare Turnstile."""

    _CLOUDFLARE_TURNSTILE_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"

    def __init__(self, secret_key: str) -> None:
        self._secret_key = secret_key

    async def verify(self, token: str, ip_address: str) -> None:
        """Verify a captcha token against Turnstile."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    self._CLOUDFLARE_TURNSTILE_URL,
                    data={
                        "secret": self._secret_key,
                        "response": token,
                        "remoteip": ip_address,
                    },
                )
                response.raise_for_status()
                data = response.json()

            if not data.get("success"):
                error_codes = data.get("error-codes", [])
                await logger.awarning("captcha_failed", error_codes=error_codes)
                raise CaptchaError("CAPTCHA verification failed", field="captcha_token")

        except CaptchaError:
            raise
        except Exception as exc:
            await logger.aerror(
                "captcha_check_skipped",
                reason="Turnstile API unavailable",
                exc_info=exc,
            )


def build_captcha_service() -> CaptchaService:
    """Build the captcha service configured by settings."""
    if not settings.captcha_enabled or not settings.captcha_secret_key:
        return StubCaptchaService()
    return CloudflareTurnstileCaptchaService(settings.captcha_secret_key)
