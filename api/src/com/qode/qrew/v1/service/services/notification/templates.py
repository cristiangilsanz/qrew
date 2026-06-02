from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from com.qode.qrew.v1.service.models.notification import NotificationChannel
from com.qode.qrew.v1.service.settings import settings
from com.qode.qrew.v1.service.templates.email_change_alert_email import (
    email_change_alert_email,
)
from com.qode.qrew.v1.service.templates.email_change_verify_email import (
    email_change_verify_email,
)
from com.qode.qrew.v1.service.templates.kyc_status_email import kyc_status_email
from com.qode.qrew.v1.service.templates.verification_link_email import (
    verification_link_email,
)
from com.qode.qrew.v1.service.templates.verification_otp_sms import verification_otp_sms


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


EMAIL_TEMPLATES: dict[str, Callable[[dict[str, Any]], RenderedEmail]] = {
    "email_verification_link": _verification_link,
    "kyc_status_email": _kyc_status,
    "email_change_verify": _email_change_verify,
    "email_change_alert": _email_change_alert,
    "account_recovery": _account_recovery,
    "login_anomaly_alert": _login_anomaly_alert,
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
