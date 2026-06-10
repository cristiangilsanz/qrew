import pytest

from com.qode.qrew.v1.service.models.notification import NotificationChannel
from com.qode.qrew.v1.service.services.notification.templates import (
    EMAIL_TEMPLATES,
    SMS_TEMPLATES,
    channel_for_template,
    render_email,
    render_sms,
)


def _sample_payload(template_key: str) -> dict[str, object]:
    samples: dict[str, dict[str, object]] = {
        "email_verification_link": {"full_name": "Ada Lovelace", "token": "tok"},
        "kyc_status_email": {
            "full_name": "Ada Lovelace",
            "status": "approved",
            "reason": None,
        },
        "email_change_verify": {"full_name": "Ada Lovelace", "token": "tok"},
        "email_change_alert": {
            "full_name": "Ada Lovelace",
            "new_email": "new@example.com",
        },
        "account_recovery": {"full_name": "Ada Lovelace"},
        "login_anomaly_alert": {
            "full_name": "Ada Lovelace",
            "reason": "impossible_travel",
            "ip_address": "127.0.0.1",
        },
        "phone_otp": {"otp": "123456"},
        "payment_succeeded": {
            "full_name": "Ada Lovelace",
            "event_name": "Wembley Show",
        },
        "payment_failed": {
            "full_name": "Ada Lovelace",
            "event_name": "Wembley Show",
            "failure_code": "card_declined",
        },
        "event_cancelled": {
            "full_name": "Ada Lovelace",
            "event_name": "Wembley Show",
        },
        "ticket_cancelled_chargeback": {
            "full_name": "Ada Lovelace",
            "event_name": "Wembley Show",
        },
        "ticket_cancelled_refund": {
            "full_name": "Ada Lovelace",
            "event_name": "Wembley Show",
        },
        "tickets_frozen_device_revoke": {
            "full_name": "Ada Lovelace",
            "ticket_count": 2,
        },
        "ticket_restored": {"full_name": "Ada Lovelace"},
    }
    return samples[template_key]


@pytest.mark.parametrize("template_key", list(EMAIL_TEMPLATES.keys()))
def test_email_template_renders_without_raising(template_key: str) -> None:
    rendered = render_email(template_key, _sample_payload(template_key))
    assert rendered.subject
    assert rendered.body_html


@pytest.mark.parametrize("template_key", list(SMS_TEMPLATES.keys()))
def test_sms_template_renders_without_raising(template_key: str) -> None:
    rendered = render_sms(template_key, _sample_payload(template_key))
    assert rendered.body


def test_channel_for_template_resolves_known_keys() -> None:
    assert channel_for_template("email_verification_link") == NotificationChannel.email
    assert channel_for_template("phone_otp") == NotificationChannel.sms


def test_channel_for_template_rejects_unknown() -> None:
    with pytest.raises(ValueError, match="unknown template_key"):
        channel_for_template("alien")
