from collections.abc import Awaitable, Callable

from com.qode.qrew.v1.service.models.notification import NotificationChannel
from com.qode.qrew.v1.service.services.notification.channels import email, sms

ChannelDeliverer = Callable[..., Awaitable[None]]

DELIVERERS: dict[NotificationChannel, ChannelDeliverer] = {
    NotificationChannel.email: email.deliver,
    NotificationChannel.sms: sms.deliver,
}


async def deliver(
    channel: NotificationChannel,
    *,
    destination: str,
    template_key: str,
    payload: dict[str, object],
) -> None:
    """Dispatch a single notification to its channel's deliverer."""
    handler = DELIVERERS[channel]
    await handler(destination=destination, template_key=template_key, payload=payload)


__all__ = ["DELIVERERS", "deliver"]
