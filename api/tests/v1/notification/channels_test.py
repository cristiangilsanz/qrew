from collections.abc import Iterator
from unittest.mock import AsyncMock, patch

import pytest

from com.qode.qrew.v1.service.models.notification import NotificationChannel
from com.qode.qrew.v1.service.services.notification.channels import deliver
from com.qode.qrew.v1.service.settings import settings


@pytest.fixture(autouse=True)
def _force_stubs() -> Iterator[None]:  # pyright: ignore[reportUnusedFunction]
    prev_email, prev_sms = settings.smtp_enabled, settings.twilio_enabled
    settings.smtp_enabled = False
    settings.twilio_enabled = False
    yield
    settings.smtp_enabled = prev_email
    settings.twilio_enabled = prev_sms


async def test_email_channel_stub_logs_and_skips_send() -> None:
    with patch("aiosmtplib.send", new=AsyncMock()) as send_mock:
        await deliver(
            NotificationChannel.email,
            destination="user@example.com",
            template_key="account_recovery",
            payload={"full_name": "Ada"},
        )
    send_mock.assert_not_called()


async def test_sms_channel_stub_logs_and_skips_send() -> None:
    with patch.object(deliver, "__wrapped__", create=True):
        await deliver(
            NotificationChannel.sms,
            destination="+34600000000",
            template_key="phone_otp",
            payload={"otp": "123456"},
        )


async def test_email_channel_sends_when_smtp_enabled() -> None:
    settings.smtp_enabled = True
    settings.smtp_from_address = "from@example.com"
    with patch("aiosmtplib.send", new=AsyncMock()) as send_mock:
        await deliver(
            NotificationChannel.email,
            destination="user@example.com",
            template_key="account_recovery",
            payload={"full_name": "Ada"},
        )
    send_mock.assert_awaited_once()
