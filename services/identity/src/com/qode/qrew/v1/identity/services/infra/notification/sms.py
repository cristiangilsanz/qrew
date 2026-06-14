from typing import Protocol

import httpx
import structlog

from com.qode.qrew.v1.identity.settings import settings
from com.qode.qrew.v1.identity.services.notification.templates.verification_otp_sms import (
    verification_otp_sms,
)

from ._masking import mask_phone_number

logger = structlog.get_logger(__name__)


class SmsService(Protocol):
    """Send transactional SMS messages."""

    async def send_otp(self, to_phone_number: str, otp: str) -> None:
        """Send a one-time password to a phone number."""
        ...


class StubSmsService:
    """Log SMS messages instead of sending them."""

    async def send_otp(self, to_phone_number: str, otp: str) -> None:
        """Log a one-time password."""
        await logger.ainfo(
            "sms_otp_stub",
            to=mask_phone_number(to_phone_number),
            otp=otp,
        )


class TwilioSmsService:
    """Send transactional SMS via the Twilio API."""

    def __init__(self, account_sid: str, auth_token: str, from_number: str) -> None:
        self._account_sid = account_sid
        self._auth_token = auth_token
        self._from_number = from_number

    @property
    def _messages_url(self) -> str:
        """Return the Twilio Messages API endpoint for this account."""
        return f"https://api.twilio.com/2010-04-01/Accounts/{self._account_sid}/Messages.json"

    async def send_otp(self, to_phone_number: str, otp: str) -> None:
        """Send a one-time password via the Twilio SMS API."""
        body = verification_otp_sms(otp, settings.phone_number_otp_expire_minutes)
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self._messages_url,
                    data={
                        "From": self._from_number,
                        "To": to_phone_number,
                        "Body": body,
                    },
                    auth=(self._account_sid, self._auth_token),
                )
                response.raise_for_status()
            await logger.ainfo("sms_otp_sent", to=mask_phone_number(to_phone_number))
        except Exception as exc:
            await logger.aerror(
                "sms_otp_failed",
                to=mask_phone_number(to_phone_number),
                exc_info=exc,
            )
