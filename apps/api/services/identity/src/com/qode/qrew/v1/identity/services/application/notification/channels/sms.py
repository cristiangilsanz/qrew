# delivers a rendered sms through twilio or logs it in development
import httpx
import structlog

from com.qode.qrew.v1.identity.services.application.notification._masking import (
    mask_phone_number as mask_phone,
)
from com.qode.qrew.v1.identity.services.application.notification.templates import render_sms
from com.qode.qrew.v1.identity.core.config import settings

logger = structlog.get_logger(__name__)


# renders and sends an sms or logs it when twilio is disabled
async def deliver(*, destination: str, template_key: str, payload: dict[str, object]) -> None:
    rendered = render_sms(template_key, dict(payload))
    if not settings.twilio_enabled:
        await logger.ainfo("sms_stub", to=mask_phone(destination), template=template_key)
        return
    url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.twilio_account_sid}/Messages.json"
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
