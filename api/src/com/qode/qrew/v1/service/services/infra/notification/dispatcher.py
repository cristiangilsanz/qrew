from typing import Protocol

from com.qode.qrew.v1.service.settings import settings

from .email import EmailService, SmtpEmailService, StubEmailService
from .sms import SmsService, StubSmsService, TwilioSmsService


class NotificationService(Protocol):
    """Dispatch transactional notifications across channels."""

    async def send_email_verification_link(
        self, to_email: str, full_name: str, token: str
    ) -> None:
        """Dispatch a verification link email."""
        ...

    async def send_sms_otp(self, to_phone_number: str, otp: str) -> None:
        """Dispatch an OTP SMS."""
        ...


class NotificationDispatcher:
    """Fan transactional events out to the configured email and SMS services."""

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

    async def send_kyc_status_update(
        self,
        to_email: str,
        full_name: str,
        status: str,
        reason: str | None,
    ) -> None:
        """Dispatch a KYC approval or rejection email."""
        await self._email.send_kyc_status(to_email, full_name, status, reason)

    async def send_email_change_verification(
        self, to_email: str, full_name: str, token: str
    ) -> None:
        """Dispatch a confirmation link to a new email address."""
        await self._email.send_email_change_verification(to_email, full_name, token)

    async def send_email_change_alert(
        self, to_email: str, full_name: str, new_email: str
    ) -> None:
        """Dispatch a security notice about an email change."""
        await self._email.send_email_change_alert(to_email, full_name, new_email)

    async def send_account_recovery(self, to_email: str, full_name: str) -> None:
        """Dispatch an account recovery security notice."""
        await self._email.send_account_recovery(to_email, full_name)

    async def send_login_anomaly_alert(
        self,
        to_email: str,
        full_name: str,
        reason: str,
        ip_address: str | None,
    ) -> None:
        """Dispatch a login anomaly security alert."""
        await self._email.send_login_anomaly_alert(
            to_email, full_name, reason, ip_address
        )


def build_notification_dispatcher() -> NotificationDispatcher:
    """Build the notification dispatcher configured by settings."""
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
