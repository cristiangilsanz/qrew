from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Protocol

import aiosmtplib
import structlog

from com.qode.qrew.v1.identity.settings import settings
from com.qode.qrew.v1.identity.templates.email_change_alert_email import (
    email_change_alert_email,
)
from com.qode.qrew.v1.identity.templates.email_change_verify_email import (
    email_change_verify_email,
)
from com.qode.qrew.v1.identity.templates.kyc_status_email import kyc_status_email
from com.qode.qrew.v1.identity.templates.verification_link_email import (
    verification_link_email,
)

from ._masking import mask_email

logger = structlog.get_logger(__name__)


class EmailService(Protocol):
    """Send transactional emails."""

    async def send_verification_link(self, to_email: str, full_name: str, token: str) -> None:
        """Send a verification link to a new account."""
        ...

    async def send_kyc_status(
        self, to_email: str, full_name: str, status: str, reason: str | None
    ) -> None:
        """Send a KYC approval or rejection notification."""
        ...

    async def send_email_change_verification(
        self, to_email: str, full_name: str, token: str
    ) -> None:
        """Send a confirmation link to a new email address."""
        ...

    async def send_email_change_alert(self, to_email: str, full_name: str, new_email: str) -> None:
        """Send a security alert about an email change."""
        ...

    async def send_account_recovery(self, to_email: str, full_name: str) -> None:
        """Send a notice that account recovery completed."""
        ...

    async def send_login_anomaly_alert(
        self,
        to_email: str,
        full_name: str,
        reason: str,
        ip_address: str | None,
    ) -> None:
        """Send a security alert for a suspicious login."""
        ...


class StubEmailService:
    """Log emails instead of sending them."""

    async def send_verification_link(self, to_email: str, full_name: str, token: str) -> None:
        """Log a verification link."""
        link = f"{settings.base_url}/verify-email?token={token}"
        await logger.ainfo(
            "email_verification_stub",
            to=mask_email(to_email),
            link_prefix=link[:60] + "…",
        )

    async def send_kyc_status(
        self, to_email: str, full_name: str, status: str, reason: str | None
    ) -> None:
        """Log a KYC status update."""
        await logger.ainfo("kyc_status_stub", to=mask_email(to_email), status=status)

    async def send_email_change_verification(
        self, to_email: str, full_name: str, token: str
    ) -> None:
        """Log an email change verification link."""
        link = f"{settings.base_url}/confirm-email-change?token={token}"
        await logger.ainfo(
            "email_change_verification_stub",
            to=mask_email(to_email),
            link_prefix=link[:60] + "…",
        )

    async def send_email_change_alert(self, to_email: str, full_name: str, new_email: str) -> None:
        """Log an email change alert."""
        await logger.ainfo("email_change_alert_stub", to=mask_email(to_email))

    async def send_account_recovery(self, to_email: str, full_name: str) -> None:
        """Log an account recovery notification."""
        await logger.ainfo("account_recovery_stub", to=mask_email(to_email))

    async def send_login_anomaly_alert(
        self,
        to_email: str,
        full_name: str,
        reason: str,
        ip_address: str | None,
    ) -> None:
        """Log a login anomaly alert."""
        await logger.awarning(
            "login_anomaly_alert_stub",
            to=mask_email(to_email),
            reason=reason,
        )


class SmtpEmailService:
    """Send transactional email via SMTP."""

    def __init__(self, host: str, port: int, user: str, password: str, from_address: str) -> None:
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._from_address = from_address

    async def send_verification_link(self, to_email: str, full_name: str, token: str) -> None:
        """Send a verification link via SMTP."""
        link = f"{settings.base_url}/verify-email?token={token}"
        expire_hours = settings.email_verification_token_expire_hours
        body = verification_link_email(full_name, link, expire_hours)
        await self._send(to_email, "Verify your Qrew account", body, "html", "email_verification")

    async def send_email_change_verification(
        self, to_email: str, full_name: str, token: str
    ) -> None:
        """Send an email change confirmation link via SMTP."""
        link = f"{settings.base_url}/confirm-email-change?token={token}"
        expire_hours = settings.email_verification_token_expire_hours
        body = email_change_verify_email(full_name, link, expire_hours)
        await self._send(
            to_email,
            "Confirm your new Qrew email address",
            body,
            "html",
            "email_change_verification",
        )

    async def send_email_change_alert(self, to_email: str, full_name: str, new_email: str) -> None:
        """Send an email change security alert via SMTP."""
        body = email_change_alert_email(full_name, new_email)
        await self._send(
            to_email,
            "Email change requested on your Qrew account",
            body,
            "html",
            "email_change_alert",
        )

    async def send_kyc_status(
        self, to_email: str, full_name: str, status: str, reason: str | None
    ) -> None:
        """Send a KYC status notification via SMTP."""
        subject = (
            "Your Qrew identity has been verified"
            if status == "approved"
            else "Qrew KYC verification update"
        )
        body = kyc_status_email(full_name, status, reason)
        await self._send(to_email, subject, body, "html", "kyc_status_email")

    async def send_login_anomaly_alert(
        self,
        to_email: str,
        full_name: str,
        reason: str,
        ip_address: str | None,
    ) -> None:
        """Send a login anomaly security alert via SMTP."""
        ip_info = f" from IP {ip_address}" if ip_address else ""
        body = (
            f"Hello {full_name},\n\n"
            f"A suspicious login{ip_info} was detected on your account.\n"
            f"Reason: {reason}\n\n"
            "If this was you, no action is needed.\n"
            "If not, secure your account immediately at "
            f"{settings.base_url}/account/security\n\n"
            "— The Qrew Team"
        )
        await self._send(
            to_email,
            "Suspicious login detected on your Qrew account",
            body,
            "plain",
            "login_anomaly_alert",
        )

    async def send_account_recovery(self, to_email: str, full_name: str) -> None:
        """Send an account recovery security notice via SMTP."""
        body = (
            f"Hello {full_name},\n\n"
            "Your Qrew account passkey was just reset via account recovery.\n"
            "If you did not initiate this, contact support immediately.\n\n"
            "— The Qrew Team"
        )
        await self._send(
            to_email,
            "Your Qrew account has been recovered",
            body,
            "plain",
            "account_recovery_email",
        )

    async def _send(
        self,
        to_email: str,
        subject: str,
        body: str,
        subtype: str,
        event: str,
    ) -> None:
        """Send a single email and log success or failure."""
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = self._from_address
        message["To"] = to_email
        message.attach(MIMEText(body, subtype))
        try:
            await aiosmtplib.send(
                message,
                hostname=self._host,
                port=self._port,
                username=self._user,
                password=self._password,
                start_tls=True,
            )
            await logger.ainfo(f"{event}_sent", to=mask_email(to_email))
        except Exception as exc:
            await logger.aerror(f"{event}_failed", to=mask_email(to_email), exc_info=exc)
