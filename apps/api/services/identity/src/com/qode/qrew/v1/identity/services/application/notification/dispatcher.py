# exposes one call per notification the identity service sends
from com.qode.qrew.v1.identity.models.notification import NotificationChannel
from com.qode.qrew.v1.identity.services.application.notification.sender import NotificationService


class NotificationDispatcher:
    # stores the notification service the dispatcher delegates to
    def __init__(self, service: NotificationService | None = None) -> None:
        self._service = service or NotificationService()

    # sends the account verification email
    async def send_email_verification_link(self, to_email: str, full_name: str, token: str) -> None:
        await self._service.send(
            template_key="email_account_verify",
            payload={"full_name": full_name, "token": token},
            channels=[NotificationChannel.email],
            destinations={NotificationChannel.email: to_email},
        )

    # sends the phone verification sms
    async def send_sms_otp(self, to_phone_number: str, otp: str) -> None:
        await self._service.send(
            template_key="sms_phone_verify",
            payload={"otp": otp},
            channels=[NotificationChannel.sms],
            destinations={NotificationChannel.sms: to_phone_number},
        )

    # sends the kyc review outcome email
    async def send_kyc_status_update(
        self,
        to_email: str,
        full_name: str,
        status: str,
        reason: str | None,
    ) -> None:
        await self._service.send(
            template_key="email_kyc_notify",
            payload={"full_name": full_name, "status": status, "reason": reason},
            channels=[NotificationChannel.email],
            destinations={NotificationChannel.email: to_email},
        )

    # sends the email address change confirmation email
    async def send_email_change_verification(
        self, to_email: str, full_name: str, token: str
    ) -> None:
        await self._service.send(
            template_key="email_address_confirm",
            payload={"full_name": full_name, "token": token},
            channels=[NotificationChannel.email],
            destinations={NotificationChannel.email: to_email},
        )

    # sends the email address changed alert
    async def send_email_change_alert(self, to_email: str, full_name: str, new_email: str) -> None:
        await self._service.send(
            template_key="email_address_changed",
            payload={"full_name": full_name, "new_email": new_email},
            channels=[NotificationChannel.email],
            destinations={NotificationChannel.email: to_email},
        )

    # sends the password reset email
    async def send_forgot_password(self, to_email: str, full_name: str, token: str) -> None:
        await self._service.send(
            template_key="email_password_reset",
            payload={"full_name": full_name, "token": token},
            channels=[NotificationChannel.email],
            destinations={NotificationChannel.email: to_email},
        )

    # sends the unusual sign in alert
    async def send_login_anomaly_alert(
        self,
        to_email: str,
        full_name: str,
        ip_address: str | None,
        location: str | None,
    ) -> None:
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


# builds a notification dispatcher
def build_notification_dispatcher() -> NotificationDispatcher:
    return NotificationDispatcher()
