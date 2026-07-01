from com.qode.qrew.v1.gateway.channels.registry import channel

_PATTERN = "entry.{event_id}"


@channel(key_pattern=_PATTERN)
async def can_subscribe_entry(claims: dict[str, object], params: dict[str, str]) -> bool:
    """Allows only scanner token holders to subscribe to entry channels."""
    del params
    return claims.get("type") == "scanner"
