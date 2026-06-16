import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

CanSubscribe = Callable[[dict[str, object], dict[str, str]], Awaitable[bool]]

_REGISTRY: dict[str, "ChannelDefinition"] = {}
_PLACEHOLDER = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


@dataclass(frozen=True)
class ChannelDefinition:
    key_pattern: str
    can_subscribe: CanSubscribe
    queue_size: int

    @property
    def _regex(self) -> re.Pattern[str]:
        escaped = re.escape(self.key_pattern)
        rebuilt = _PLACEHOLDER.sub(
            lambda m: f"(?P<{re.escape(m.group(1)).replace(chr(92), '')}>[^.]+)",
            escaped.replace(r"\{", "{").replace(r"\}", "}"),
        )
        return re.compile(f"^{rebuilt}$")

    def match(self, channel_key: str) -> dict[str, str] | None:
        m = self._regex.fullmatch(channel_key)
        return m.groupdict() if m else None


def channel(*, key_pattern: str, queue_size: int = 64) -> Callable[[CanSubscribe], CanSubscribe]:
    def decorator(func: CanSubscribe) -> CanSubscribe:
        if key_pattern in _REGISTRY:
            raise ValueError(f"duplicate channel pattern: {key_pattern}")
        _REGISTRY[key_pattern] = ChannelDefinition(
            key_pattern=key_pattern,
            can_subscribe=func,
            queue_size=queue_size,
        )
        return func

    return decorator


def resolve(channel_key: str) -> tuple[ChannelDefinition, dict[str, str]] | None:
    for definition in _REGISTRY.values():
        params = definition.match(channel_key)
        if params is not None:
            return definition, params
    return None
