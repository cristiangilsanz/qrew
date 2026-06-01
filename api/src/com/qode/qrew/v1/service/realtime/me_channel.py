from com.qode.qrew.v1.service.core.ws import channel
from com.qode.qrew.v1.service.models.auth.session import Session
from com.qode.qrew.v1.service.models.auth.user import User

_PATTERN = "me.{user_id}"


@channel(key_pattern=_PATTERN)
async def can_subscribe_me(
    user: User, params: dict[str, str], session: Session
) -> bool:
    """Only the owning user may subscribe to their personal channel."""
    del session
    return params.get("user_id") == str(user.id)


def me_channel_key(user_id: str) -> str:
    """Return the channel key used to publish events for a specific user."""
    return _PATTERN.format(user_id=user_id)
