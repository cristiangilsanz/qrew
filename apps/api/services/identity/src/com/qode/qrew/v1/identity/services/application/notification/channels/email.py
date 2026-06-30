from email.message import EmailMessage

import aiosmtplib
import structlog

from com.qode.qrew.v1.identity.services.application.notification._masking import mask_email
from com.qode.qrew.v1.identity.services.application.notification.templates import (
    RenderedEmail,
    render_email,
)
from com.qode.qrew.v1.identity.core.config import settings

logger = structlog.get_logger(__name__)


async def deliver(*, destination: str, template_key: str, payload: dict[str, object]) -> None:
    """Render and send an email, or log to the stub when SMTP is disabled."""
    rendered = render_email(template_key, dict(payload))
    if not settings.smtp_enabled:
        await logger.ainfo("email_stub", to=mask_email(destination), template=template_key)
        return
    await _smtp_send(destination, rendered)


async def _smtp_send(destination: str, rendered: RenderedEmail) -> None:
    message = EmailMessage()
    message["From"] = settings.smtp_from_address
    message["To"] = destination
    message["Subject"] = rendered.subject
    message.set_content("Please view this email in an HTML-capable client.")
    message.add_alternative(rendered.body_html, subtype="html")
    await aiosmtplib.send(
        message,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_user,
        password=settings.smtp_password,
        start_tls=True,
    )
