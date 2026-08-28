# authorizes subscriptions to a control device's entry channel
from com.qode.qrew.v1.gateway.channels.registry import channel

_PATTERN = "entry.{event_id}"


# allows only scanner identities to subscribe to an entry channel
@channel(key_pattern=_PATTERN)
async def can_subscribe_entry(claims: dict[str, object], params: dict[str, str]) -> bool:
    del params
    return claims.get("type") == "scanner"
