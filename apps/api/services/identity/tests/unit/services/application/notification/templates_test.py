# covers the notification template registry and what each template renders
import pytest

from com.qode.qrew.v1.identity.models.notification import NotificationChannel
from com.qode.qrew.v1.identity.services.application.notification import templates

FULL_NAME = "Jane Doe"
FIRST_NAME = "Jane"


class TestChannelForTemplate:
    # verifies that every email template resolves to the email channel
    @pytest.mark.parametrize("key", sorted(templates.EMAIL_TEMPLATES))
    def test_an_email_template_resolves_to_the_email_channel(self, key: str) -> None:
        assert templates.channel_for_template(key) is NotificationChannel.email

    # verifies that every sms template resolves to the sms channel
    @pytest.mark.parametrize("key", sorted(templates.SMS_TEMPLATES))
    def test_an_sms_template_resolves_to_the_sms_channel(self, key: str) -> None:
        assert templates.channel_for_template(key) is NotificationChannel.sms

    # verifies that an unknown key is rejected
    def test_an_unknown_key_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="unknown template_key"):
            templates.channel_for_template("nope")


class TestRenderEmail:
    # verifies that every email template renders a subject and a body carrying the logo
    @pytest.mark.parametrize(
        ("key", "payload"),
        [
            ("email_account_verify", {"full_name": FULL_NAME, "token": "tok"}),
            ("email_kyc_notify", {"full_name": FULL_NAME, "status": "approved"}),
            ("email_address_confirm", {"full_name": FULL_NAME, "token": "tok"}),
            ("email_address_changed", {"full_name": FULL_NAME, "new_email": "new@example.com"}),
            ("email_login_alert", {"full_name": FULL_NAME}),
            ("email_password_reset", {"full_name": FULL_NAME, "token": "tok"}),
        ],
    )
    def test_every_template_renders(self, key: str, payload: dict[str, object]) -> None:
        rendered = templates.render_email(key, payload)
        assert rendered.subject
        assert FIRST_NAME in rendered.body_html
        assert "/logo.png" in rendered.body_html

    # verifies that the verification email carries the link the recipient must open
    def test_the_verification_email_carries_the_link(self) -> None:
        rendered = templates.render_email(
            "email_account_verify", {"full_name": FULL_NAME, "token": "abc123"}
        )
        assert "/verify-email?token=abc123" in rendered.body_html

    # verifies that the password reset email carries the reset link
    def test_the_password_reset_email_carries_the_link(self) -> None:
        rendered = templates.render_email(
            "email_password_reset", {"full_name": FULL_NAME, "token": "abc123"}
        )
        assert "/reset-password?token=abc123" in rendered.body_html

    # verifies that an approved review and a rejected one read differently
    def test_the_kyc_email_reads_differently_by_outcome(self) -> None:
        approved = templates.render_email(
            "email_kyc_notify", {"full_name": FULL_NAME, "status": "approved"}
        )
        rejected = templates.render_email(
            "email_kyc_notify",
            {"full_name": FULL_NAME, "status": "rejected", "reason": "Blurred photo."},
        )
        assert approved.subject != rejected.subject
        assert approved.body_html != rejected.body_html

    # verifies that a sign in alert without a location still renders
    def test_the_login_alert_survives_a_missing_location(self) -> None:
        rendered = templates.render_email("email_login_alert", {"full_name": FULL_NAME})
        assert "unknown" in rendered.body_html


class TestRenderSms:
    # verifies that the phone verification sms carries the code
    def test_the_phone_verification_sms_carries_the_code(self) -> None:
        assert "123456" in templates.render_sms("sms_phone_verify", {"otp": "123456"}).body
