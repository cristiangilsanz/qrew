from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from com.qode.qrew.v1.identity.models.notification import NotificationChannel
from com.qode.qrew.v1.identity.core.config import settings
from com.qode.qrew.v1.identity.services.application.notification.templates.email_address_changed import (
    email_change_alert_email,
)
from com.qode.qrew.v1.identity.services.application.notification.templates.email_address_confirm import (
    email_change_verify_email,
)
from com.qode.qrew.v1.identity.services.application.notification.templates.email_account_verify import (
    verification_link_email,
)
from com.qode.qrew.v1.identity.services.application.notification.templates.email_password_reset import (
    forgot_password_email,
)
from com.qode.qrew.v1.identity.services.application.notification.templates.email_kyc_notify import (
    kyc_status_email,
)
from com.qode.qrew.v1.identity.services.application.notification.templates.email_login_alert import (
    login_anomaly_alert_email,
)
from com.qode.qrew.v1.identity.services.application.notification.templates.sms_phone_verify import (
    verification_otp_sms,
)


@dataclass(frozen=True)
class RenderedEmail:
    subject: str
    body_html: str


@dataclass(frozen=True)
class RenderedSms:
    body: str


def _logo_url() -> str:
    return f"{settings.base_url}/logo.webp"


def _verification_link(payload: dict[str, Any]) -> RenderedEmail:
    link = f"{settings.base_url}/verify-email?token={payload['token']}"
    return RenderedEmail(
        subject="Verify your Qrew account",
        body_html=verification_link_email(
            full_name=payload["full_name"],
            link=link,
            expire_hours=settings.email_verification_token_expire_hours,
            logo_url=_logo_url(),
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
            logo_url=_logo_url(),
        ),
    )


def _email_address_confirm(payload: dict[str, Any]) -> RenderedEmail:
    link = f"{settings.base_url}/verify-email-change?token={payload['token']}"
    return RenderedEmail(
        subject="Confirm your new Qrew email",
        body_html=email_change_verify_email(
            full_name=payload["full_name"],
            link=link,
            expire_hours=settings.email_verification_token_expire_hours,
            logo_url=_logo_url(),
        ),
    )


def _email_address_changed(payload: dict[str, Any]) -> RenderedEmail:
    return RenderedEmail(
        subject="Your Qrew email was changed",
        body_html=email_change_alert_email(
            full_name=payload["full_name"],
            new_email=payload["new_email"],
            logo_url=_logo_url(),
        ),
    )


def _login_anomaly_alert(payload: dict[str, Any]) -> RenderedEmail:
    return RenderedEmail(
        subject="Unusual sign-in to your Qrew account",
        body_html=login_anomaly_alert_email(
            full_name=payload["full_name"],
            ip_address=payload.get("ip_address") or "unknown",
            location=payload.get("location"),
            logo_url=_logo_url(),
        ),
    )


def _password_reset(payload: dict[str, Any]) -> RenderedEmail:
    link = f"{settings.base_url}/reset-password?token={payload['token']}"
    return RenderedEmail(
        subject="Reset your Qrew password",
        body_html=forgot_password_email(
            full_name=payload["full_name"],
            link=link,
            expire_hours=settings.email_verification_token_expire_hours,
            logo_url=_logo_url(),
        ),
    )


def _phone_verify(payload: dict[str, Any]) -> RenderedSms:
    return RenderedSms(
        body=verification_otp_sms(
            otp=payload["otp"],
            expire_minutes=settings.phone_number_otp_expire_minutes,
        )
    )


EMAIL_TEMPLATES: dict[str, Callable[[dict[str, Any]], RenderedEmail]] = {
    "email_account_verify": _verification_link,
    "email_kyc_notify": _kyc_status,
    "email_address_confirm": _email_address_confirm,
    "email_address_changed": _email_address_changed,
    "email_login_alert": _login_anomaly_alert,
    "email_password_reset": _password_reset,
}

SMS_TEMPLATES: dict[str, Callable[[dict[str, Any]], RenderedSms]] = {
    "sms_phone_verify": _phone_verify,
}


def channel_for_template(template_key: str) -> NotificationChannel:
    if template_key in EMAIL_TEMPLATES:
        return NotificationChannel.email
    if template_key in SMS_TEMPLATES:
        return NotificationChannel.sms
    raise ValueError(f"unknown template_key: {template_key}")


def render_email(template_key: str, payload: dict[str, Any]) -> RenderedEmail:
    return EMAIL_TEMPLATES[template_key](payload)


def render_sms(template_key: str, payload: dict[str, Any]) -> RenderedSms:
    return SMS_TEMPLATES[template_key](payload)
