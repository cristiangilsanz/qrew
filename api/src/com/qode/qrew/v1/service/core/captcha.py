from typing import Protocol

import httpx
import structlog

from com.qode.qrew.v1.service.core.errors import DomainError
from com.qode.qrew.v1.service.settings import settings

logger = structlog.get_logger(__name__)


class CaptchaError(DomainError):
    """A business-rule violation raised when a CAPTCHA token cannot be verified."""


class CaptchaService(Protocol):
    async def verify(self, token: str, ip_address: str) -> None:
        """Raise ``CaptchaError`` if the token is invalid or expired."""
        ...


class StubCaptchaService:
    """Stubs Captcha service."""

    async def verify(self, token: str, ip_address: str) -> None:
        pass


class CloudflareTurnstileCaptchaService:
    """Cloudflare Turnstile Captcha service."""

    _CLOUDFLARE_TURNSTILE_URL = (
        "https://challenges.cloudflare.com/turnstile/v0/siteverify"
    )

    def __init__(self, secret_key: str) -> None:
        self._secret_key = secret_key

    async def verify(self, token: str, ip_address: str) -> None:
        """Verify the token."""
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
    """Return the appropriate CAPTCHA service."""
    if not settings.captcha_enabled or not settings.captcha_secret_key:
        return StubCaptchaService()
    return CloudflareTurnstileCaptchaService(settings.captcha_secret_key)
