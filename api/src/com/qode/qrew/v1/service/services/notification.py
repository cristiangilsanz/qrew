import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Protocol

import aiosmtplib
import httpx
import structlog

from com.qode.qrew.v1.service.settings import settings
from com.qode.qrew.v1.service.templates.verification_link_email import (
    verification_link_email,
)
from com.qode.qrew.v1.service.templates.verification_otp_sms import verification_otp_sms

logger = structlog.get_logger(__name__)

_DIGIT_RE = re.compile(r"\D")


def _mask_email(email: str) -> str:
    """``alice@example.com`` → ``a***@example.com``."""
    local, domain = email.split("@", 1)
    return f"{local[0]}***@{domain}"


def _mask_phone_number(phone_number: str) -> str:
    """``+1 555 123 4567`` → ``****4567``."""
    digits = _DIGIT_RE.sub("", phone_number)
    return f"****{digits[-4:]}"


class EmailService(Protocol):
    """Sends a single type of transactional email."""

    async def send_verification_link(
        self, to_email: str, full_name: str, token: str
    ) -> None:
        """Send a verification link to the given email address."""
        ...


class SmsService(Protocol):
    """Sends a single type of transactional SMS."""

    async def send_otp(self, to_phone_number: str, otp: str) -> None:
        """Send an OTP to the given phone number."""
        ...


class NotificationService(Protocol):
    async def send_email_verification_link(
        self, to_email: str, full_name: str, token: str
    ) -> None:
        """Dispatch a verification link email."""
        ...

    async def send_sms_otp(self, to_phone_number: str, otp: str) -> None:
        """Dispatch an OTP SMS."""
        ...


class StubEmailService:
    """Stub Email Service"""

    async def send_verification_link(
        self, to_email: str, full_name: str, token: str
    ) -> None:
        """Log verification link."""
        link = f"{settings.base_url}/verify-email?token={token}"
        await logger.ainfo(
            "email_verification_stub",
            to=_mask_email(to_email),
            link_prefix=link[:60] + "…",
        )


class StubSmsService:
    """Stub SMS Service"""

    async def send_otp(self, to_phone_number: str, otp: str) -> None:
        """Log OTP."""
        await logger.ainfo(
            "sms_otp_stub",
            to=_mask_phone_number(to_phone_number),
            otp=otp,
        )


class SmtpEmailService:
    """Sends transactional email via SMTP."""

    def __init__(
        self, host: str, port: int, user: str, password: str, from_address: str
    ) -> None:
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._from_address = from_address

    async def send_verification_link(
        self, to_email: str, full_name: str, token: str
    ) -> None:
        """Send a verification link via SMTP."""
        link = f"{settings.base_url}/verify-email?token={token}"
        expire_hours = settings.email_verification_token_expire_hours

        message = MIMEMultipart("alternative")
        message["Subject"] = "Verify your Qrew account"
        message["From"] = self._from_address
        message["To"] = to_email
        message.attach(
            MIMEText(verification_link_email(full_name, link, expire_hours), "html")
        )

        try:
            await aiosmtplib.send(
                message,
                hostname=self._host,
                port=self._port,
                username=self._user,
                password=self._password,
                start_tls=True,
            )
            await logger.ainfo("email_verification_sent", to=_mask_email(to_email))
        except Exception as exc:
            await logger.aerror(
                "email_verification_failed", to=_mask_email(to_email), exc_info=exc
            )


class TwilioSmsService:
    def __init__(self, account_sid: str, auth_token: str, from_number: str) -> None:
        self._account_sid = account_sid
        self._auth_token = auth_token
        self._from_number = from_number

    @property
    def _messages_url(self) -> str:
        """Return the Twilio Messages API URL for this account."""
        return (
            f"https://api.twilio.com/2010-04-01/Accounts"
            f"/{self._account_sid}/Messages.json"
        )

    async def send_otp(self, to_phone_number: str, otp: str) -> None:
        """Send an OTP via the Twilio SMS API."""
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
            await logger.ainfo("sms_otp_sent", to=_mask_phone_number(to_phone_number))
        except Exception as exc:
            await logger.aerror(
                "sms_otp_failed", to=_mask_phone_number(to_phone_number), exc_info=exc
            )


class NotificationDispatcher:
    def __init__(self, email: EmailService, sms: SmsService) -> None:
        self._email = email
        self._sms = sms

    async def send_email_verification_link(
        self, to_email: str, full_name: str, token: str
    ) -> None:
        """Dispatch an email verification link."""
        await self._email.send_verification_link(to_email, full_name, token)

    async def send_sms_otp(self, to_phone_number: str, otp: str) -> None:
        """Dispatch an SMS OTP."""
        await self._sms.send_otp(to_phone_number, otp)


def build_notification_dispatcher() -> NotificationDispatcher:
    """Return the appropriate notification dispatcher."""
    email: EmailService = (
        SmtpEmailService(
            settings.smtp_host,
            settings.smtp_port,
            settings.smtp_user,
            settings.smtp_password,
            settings.smtp_from_address,
        )
        if settings.smtp_enabled
        else StubEmailService()
    )
    sms: SmsService = (
        TwilioSmsService(
            settings.twilio_account_sid,
            settings.twilio_auth_token,
            settings.twilio_from_number,
        )
        if settings.twilio_enabled
        else StubSmsService()
    )
    return NotificationDispatcher(email, sms)
