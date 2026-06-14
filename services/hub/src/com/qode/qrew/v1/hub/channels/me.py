from com.qode.qrew.v1.hub.channels.registry import channel

_PATTERN = "me.{user_id}"


@channel(key_pattern=_PATTERN)
async def can_subscribe_me(claims: dict[str, object], params: dict[str, str]) -> bool:
    """Only the owning user may subscribe to their personal channel."""
    return params.get("user_id") == str(claims.get("sub", ""))


def me_channel_key(user_id: str) -> str:
    return _PATTERN.format(user_id=user_id)
