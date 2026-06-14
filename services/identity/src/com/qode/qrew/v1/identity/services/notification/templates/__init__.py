from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from com.qode.qrew.v1.identity.models.notification import NotificationChannel
from com.qode.qrew.v1.identity.settings import settings
from com.qode.qrew.v1.identity.services.notification.templates.email_change_alert_email import (
    email_change_alert_email,
)
from com.qode.qrew.v1.identity.services.notification.templates.lifecycle_emails import (
    event_cancelled_email,
    payment_failed_email,
    payment_succeeded_email,
    ticket_cancelled_email,
    ticket_restored_email,
    tickets_frozen_email,
)
from com.qode.qrew.v1.identity.services.notification.templates.email_change_verify_email import (
    email_change_verify_email,
)
from com.qode.qrew.v1.identity.services.notification.templates.kyc_status_email import (
    kyc_status_email,
)
from com.qode.qrew.v1.identity.services.notification.templates.verification_link_email import (
    verification_link_email,
)
from com.qode.qrew.v1.identity.services.notification.templates.verification_otp_sms import (
    verification_otp_sms,
)


@dataclass(frozen=True)
class RenderedEmail:
    subject: str
    body_html: str


@dataclass(frozen=True)
class RenderedSms:
    body: str


def _verification_link(payload: dict[str, Any]) -> RenderedEmail:
    link = f"{settings.base_url}/verify-email?token={payload['token']}"
    return RenderedEmail(
        subject="Verify your Qrew account",
        body_html=verification_link_email(
            full_name=payload["full_name"],
            link=link,
            expire_hours=settings.email_verification_token_expire_hours,
        ),
    )


def _kyc_status(payload: dict[str, Any]) -> RenderedEmail:
    status = str(payload["status"])
    subject = (
        "Your Qrew account is verified"
        if status == "approved"
        else "Your Qrew identity check needs attention"
    )
    return RenderedEmail(
        subject=subject,
        body_html=kyc_status_email(
            full_name=payload["full_name"],
            status=status,
            reason=payload.get("reason"),
        ),
    )


def _email_change_verify(payload: dict[str, Any]) -> RenderedEmail:
    link = f"{settings.base_url}/verify-email-change?token={payload['token']}"
    return RenderedEmail(
        subject="Confirm your new Qrew email",
        body_html=email_change_verify_email(
            full_name=payload["full_name"],
            link=link,
            expire_hours=settings.email_verification_token_expire_hours,
        ),
    )


def _email_change_alert(payload: dict[str, Any]) -> RenderedEmail:
    return RenderedEmail(
        subject="Your Qrew email was changed",
        body_html=email_change_alert_email(
            full_name=payload["full_name"],
            new_email=payload["new_email"],
        ),
    )


def _account_recovery(payload: dict[str, Any]) -> RenderedEmail:
    return RenderedEmail(
        subject="Your Qrew account was recovered",
        body_html=(
            f"<p>Hi {payload['full_name']},</p>"
            "<p>Your account was just recovered. If this was not you, "
            "contact support immediately.</p>"
        ),
    )


def _login_anomaly_alert(payload: dict[str, Any]) -> RenderedEmail:
    ip = payload.get("ip_address") or "unknown"
    return RenderedEmail(
        subject="Unusual sign-in to your Qrew account",
        body_html=(
            f"<p>Hi {payload['full_name']},</p>"
            f"<p>We detected an unusual sign-in: {payload['reason']} from {ip}.</p>"
            "<p>If that wasn't you, change your password and revoke sessions.</p>"
        ),
    )


def _phone_otp(payload: dict[str, Any]) -> RenderedSms:
    return RenderedSms(
        body=verification_otp_sms(
            otp=payload["otp"],
            expire_minutes=settings.phone_number_otp_expire_minutes,
        )
    )


def _payment_succeeded(payload: dict[str, Any]) -> RenderedEmail:
    return RenderedEmail(
        subject="Your Qrew payment succeeded",
        body_html=payment_succeeded_email(
            full_name=payload.get("full_name", "there"),
            event_name=payload.get("event_name", "your event"),
        ),
    )


def _payment_failed(payload: dict[str, Any]) -> RenderedEmail:
    return RenderedEmail(
        subject="Your Qrew payment failed",
        body_html=payment_failed_email(
            full_name=payload.get("full_name", "there"),
            event_name=payload.get("event_name", "your event"),
            reason=payload.get("failure_code"),
        ),
    )


def _event_cancelled(payload: dict[str, Any]) -> RenderedEmail:
    return RenderedEmail(
        subject="An event you reserved has been cancelled",
        body_html=event_cancelled_email(
            full_name=payload.get("full_name", "there"),
            event_name=payload.get("event_name", "your event"),
        ),
    )


def _ticket_cancelled_chargeback(payload: dict[str, Any]) -> RenderedEmail:
    return RenderedEmail(
        subject="Your Qrew ticket was cancelled (chargeback)",
        body_html=ticket_cancelled_email(
            full_name=payload.get("full_name", "there"),
            event_name=payload.get("event_name", "your event"),
            reason="chargeback opened",
        ),
    )


def _ticket_cancelled_refund(payload: dict[str, Any]) -> RenderedEmail:
    return RenderedEmail(
        subject="Your Qrew ticket was refunded",
        body_html=ticket_cancelled_email(
            full_name=payload.get("full_name", "there"),
            event_name=payload.get("event_name", "your event"),
            reason="refund",
        ),
    )


def _tickets_frozen_device_revoke(payload: dict[str, Any]) -> RenderedEmail:
    return RenderedEmail(
        subject="Tickets frozen on revoked device",
        body_html=tickets_frozen_email(
            full_name=payload.get("full_name", "there"),
            ticket_count=int(payload.get("ticket_count", 0)),
        ),
    )


def _ticket_restored(payload: dict[str, Any]) -> RenderedEmail:
    return RenderedEmail(
        subject="Your Qrew ticket is restored",
        body_html=ticket_restored_email(full_name=payload.get("full_name", "there")),
    )


EMAIL_TEMPLATES: dict[str, Callable[[dict[str, Any]], RenderedEmail]] = {
    "email_verification_link": _verification_link,
    "kyc_status_email": _kyc_status,
    "email_change_verify": _email_change_verify,
    "email_change_alert": _email_change_alert,
    "account_recovery": _account_recovery,
    "login_anomaly_alert": _login_anomaly_alert,
    "payment_succeeded": _payment_succeeded,
    "payment_failed": _payment_failed,
    "event_cancelled": _event_cancelled,
    "ticket_cancelled_chargeback": _ticket_cancelled_chargeback,
    "ticket_cancelled_refund": _ticket_cancelled_refund,
    "tickets_frozen_device_revoke": _tickets_frozen_device_revoke,
    "ticket_restored": _ticket_restored,
}

SMS_TEMPLATES: dict[str, Callable[[dict[str, Any]], RenderedSms]] = {
    "phone_otp": _phone_otp,
}


def channel_for_template(template_key: str) -> NotificationChannel:
    """Map a registered template key to the channel it belongs to."""
    if template_key in EMAIL_TEMPLATES:
        return NotificationChannel.email
    if template_key in SMS_TEMPLATES:
        return NotificationChannel.sms
    raise ValueError(f"unknown template_key: {template_key}")


def render_email(template_key: str, payload: dict[str, Any]) -> RenderedEmail:
    """Render an email template by key."""
    return EMAIL_TEMPLATES[template_key](payload)


def render_sms(template_key: str, payload: dict[str, Any]) -> RenderedSms:
    """Render an SMS template by key."""
    return SMS_TEMPLATES[template_key](payload)
