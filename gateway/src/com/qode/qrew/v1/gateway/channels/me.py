from com.qode.qrew.v1.gateway.channels.registry import channel

_PATTERN = "me.{user_id}"


@channel(key_pattern=_PATTERN)
async def can_subscribe_me(claims: dict[str, object], params: dict[str, str]) -> bool:
    """Only the owning user may subscribe to their personal channel."""
    return params.get("user_id") == str(claims.get("sub", ""))
