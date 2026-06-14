from com.qode.qrew.v1.identity.models.notification import NotificationChannel
from com.qode.qrew.v1.identity.services.notification import NotificationService


class NotificationDispatcher:
    """Routes notification requests through the unified notification service."""

    def __init__(self, service: NotificationService | None = None) -> None:
        self._service = service or NotificationService()

    async def send_email_verification_link(self, to_email: str, full_name: str, token: str) -> None:
        """Dispatch an email verification link."""
        await self._service.send(
            template_key="email_verification_link",
            payload={"full_name": full_name, "token": token},
            channels=[NotificationChannel.email],
            destinations={NotificationChannel.email: to_email},
        )

    async def send_sms_otp(self, to_phone_number: str, otp: str) -> None:
        """Dispatch an SMS OTP."""
        await self._service.send(
            template_key="phone_otp",
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
            template_key="kyc_status_email",
            payload={"full_name": full_name, "status": status, "reason": reason},
            channels=[NotificationChannel.email],
            destinations={NotificationChannel.email: to_email},
        )

    async def send_email_change_verification(
        self, to_email: str, full_name: str, token: str
    ) -> None:
        """Dispatch a confirmation link to a new email address."""
        await self._service.send(
            template_key="email_change_verify",
            payload={"full_name": full_name, "token": token},
            channels=[NotificationChannel.email],
            destinations={NotificationChannel.email: to_email},
        )

    async def send_email_change_alert(self, to_email: str, full_name: str, new_email: str) -> None:
        """Dispatch a security notice about an email change."""
        await self._service.send(
            template_key="email_change_alert",
            payload={"full_name": full_name, "new_email": new_email},
            channels=[NotificationChannel.email],
            destinations={NotificationChannel.email: to_email},
        )

    async def send_account_recovery(self, to_email: str, full_name: str) -> None:
        """Dispatch an account recovery security notice."""
        await self._service.send(
            template_key="account_recovery",
            payload={"full_name": full_name},
            channels=[NotificationChannel.email],
            destinations={NotificationChannel.email: to_email},
        )

    async def send_login_anomaly_alert(
        self,
        to_email: str,
        full_name: str,
        reason: str,
        ip_address: str | None,
    ) -> None:
        """Dispatch a login anomaly security alert."""
        await self._service.send(
            template_key="login_anomaly_alert",
            payload={
                "full_name": full_name,
                "reason": reason,
                "ip_address": ip_address,
            },
            channels=[NotificationChannel.email],
            destinations={NotificationChannel.email: to_email},
        )


def build_notification_dispatcher() -> NotificationDispatcher:
    """Constructs and returns a fully wired notification dispatcher."""
    return NotificationDispatcher()
