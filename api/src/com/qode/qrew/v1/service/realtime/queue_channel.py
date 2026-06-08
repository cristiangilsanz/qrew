from com.qode.qrew.v1.service.core.ws import channel
from com.qode.qrew.v1.service.models.auth.session import Session
from com.qode.qrew.v1.service.models.auth.user import User

_PATTERN = "queue.{event_id}.{user_id}"


@channel(key_pattern=_PATTERN)
async def can_subscribe_queue(
    user: User, params: dict[str, str], session: Session
) -> bool:
    """Each user subscribes to their own slot on a queue."""
    del session
    return params.get("user_id") == str(user.id)


def queue_channel_key(event_id: str, user_id: str) -> str:
    """Return the channel key used to publish redeem tokens for one slot."""
    return _PATTERN.format(event_id=event_id, user_id=user_id)
