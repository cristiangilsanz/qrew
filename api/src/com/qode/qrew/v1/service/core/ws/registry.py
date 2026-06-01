import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from com.qode.qrew.v1.service.models.auth.session import Session
from com.qode.qrew.v1.service.models.auth.user import User

CanSubscribe = Callable[[User, dict[str, str], Session], Awaitable[bool]]


@dataclass(frozen=True)
class ChannelDefinition:
    key_pattern: str
    can_subscribe: CanSubscribe
    queue_size: int

    @property
    def regex(self) -> re.Pattern[str]:
        return _compile_pattern(self.key_pattern)

    def match(self, channel_key: str) -> dict[str, str] | None:
        m = self.regex.fullmatch(channel_key)
        return m.groupdict() if m else None


_REGISTRY: dict[str, ChannelDefinition] = {}
_PLACEHOLDER = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


def _compile_pattern(pattern: str) -> re.Pattern[str]:
    escaped = re.escape(pattern)
    rebuilt = _PLACEHOLDER.sub(
        lambda match: f"(?P<{re.escape(match.group(1)).replace(chr(92), '')}>[^.]+)",
        escaped.replace(r"\{", "{").replace(r"\}", "}"),
    )
    return re.compile(f"^{rebuilt}$")


def channel(
    *, key_pattern: str, queue_size: int = 64
) -> Callable[[CanSubscribe], CanSubscribe]:
    """Register a channel definition keyed by its pattern."""

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
    """Find the channel definition that matches the requested key."""
    for definition in _REGISTRY.values():
        params = definition.match(channel_key)
        if params is not None:
            return definition, params
    return None


def all_channels() -> list[ChannelDefinition]:
    return list(_REGISTRY.values())


def reset_for_tests() -> None:
    _REGISTRY.clear()


def _placeholder_names(pattern: str) -> list[str]:
    return [m.group(1) for m in _PLACEHOLDER.finditer(pattern)]


def render_key(pattern: str, params: dict[str, str | Any]) -> str:
    """Substitute placeholders in a channel pattern with concrete values."""
    rendered = pattern
    for name in _placeholder_names(pattern):
        rendered = rendered.replace(f"{{{name}}}", str(params[name]))
    return rendered
