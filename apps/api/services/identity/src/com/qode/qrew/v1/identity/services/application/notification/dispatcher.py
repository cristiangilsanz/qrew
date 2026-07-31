from com.qode.qrew.v1.identity.models.notification import NotificationChannel
from com.qode.qrew.v1.identity.services.application.notification.sender import NotificationService


class NotificationDispatcher:
    """Routes notification requests through the unified notification service."""

    def __init__(self, service: NotificationService | None = None) -> None:
        self._service = service or NotificationService()

    async def send_email_verification_link(self, to_email: str, full_name: str, token: str) -> None:
        """Dispatch an email verification link."""
        await self._service.send(
            template_key="email_account_verify",
            payload={"full_name": full_name, "token": token},
            channels=[NotificationChannel.email],
            destinations={NotificationChannel.email: to_email},
        )

    async def send_sms_otp(self, to_phone_number: str, otp: str) -> None:
        """Dispatch an SMS OTP."""
        await self._service.send(
            template_key="sms_phone_verify",
            payload={"otp": otp},
            channels=[NotificationChannel.sms],
            destinations={NotificationChannel.sms: to_phone_number},
        )

    async def send_kyc_status_update(
        self,
        to_email: str,
        full_name: str,
        status: str,
        reason: str | None,
    ) -> None:
        """Dispatch a KYC approval or rejection email."""
        await self._service.send(
            template_key="email_kyc_notify",
            payload={"full_name": full_name, "status": status, "reason": reason},
            channels=[NotificationChannel.email],
            destinations={NotificationChannel.email: to_email},
        )

    async def send_email_change_verification(
        self, to_email: str, full_name: str, token: str
    ) -> None:
        """Dispatch a confirmation link to a new email address."""
        await self._service.send(
            template_key="email_address_confirm",
            payload={"full_name": full_name, "token": token},
            channels=[NotificationChannel.email],
            destinations={NotificationChannel.email: to_email},
        )

    async def send_email_change_alert(self, to_email: str, full_name: str, new_email: str) -> None:
        """Dispatch a security notice about an email change."""
        await self._service.send(
            template_key="email_address_changed",
            payload={"full_name": full_name, "new_email": new_email},
            channels=[NotificationChannel.email],
            destinations={NotificationChannel.email: to_email},
        )

    async def send_forgot_password(self, to_email: str, full_name: str, token: str) -> None:
        """Dispatch a password reset link."""
        await self._service.send(
            template_key="email_password_reset",
            payload={"full_name": full_name, "token": token},
            channels=[NotificationChannel.email],
            destinations={NotificationChannel.email: to_email},
        )

    async def send_login_anomaly_alert(
        self,
        to_email: str,
        full_name: str,
        ip_address: str | None,
        location: str | None,
    ) -> None:
        """Dispatch a login anomaly security alert."""
        await self._service.send(
            template_key="email_login_alert",
            payload={
                "full_name": full_name,
                "ip_address": ip_address,
                "location": location,
            },
            channels=[NotificationChannel.email],
            destinations={NotificationChannel.email: to_email},
        )


def build_notification_dispatcher() -> NotificationDispatcher:
    """Constructs and returns a fully wired notification dispatcher."""
    return NotificationDispatcher()
