import httpx
import structlog

from com.qode.qrew.v1.service.services.infra.notification._masking import (
    mask_phone_number as mask_phone,
)
from com.qode.qrew.v1.service.services.notification.templates import render_sms
from com.qode.qrew.v1.service.settings import settings

logger = structlog.get_logger(__name__)


async def deliver(
    *, destination: str, template_key: str, payload: dict[str, object]
) -> None:
    """Render and send an SMS, or log to the stub when Twilio is disabled."""
    rendered = render_sms(template_key, dict(payload))
    if not settings.twilio_enabled:
        await logger.ainfo(
            "sms_stub", to=mask_phone(destination), template=template_key
        )
        return
    url = (
        f"https://api.twilio.com/2010-04-01/Accounts"
        f"/{settings.twilio_account_sid}/Messages.json"
    )
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            url,
            data={
                "From": settings.twilio_from_number,
                "To": destination,
                "Body": rendered.body,
            },
            auth=(settings.twilio_account_sid, settings.twilio_auth_token),
        )
        response.raise_for_status()
