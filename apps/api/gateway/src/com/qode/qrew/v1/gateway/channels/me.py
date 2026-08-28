# authorizes subscriptions to a user's own channel
from com.qode.qrew.v1.gateway.channels.registry import channel

_PATTERN = "me.{user_id}"


# allows a user to subscribe only to their own channel
@channel(key_pattern=_PATTERN)
async def can_subscribe_me(claims: dict[str, object], params: dict[str, str]) -> bool:
    return params.get("user_id") == str(claims.get("sub", ""))
