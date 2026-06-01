from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Literal

Scope = Literal["user", "global"]


@dataclass(frozen=True)
class IdempotencyConfig:
    scope: Scope
    ttl_seconds: int
    required: bool


_ATTR = "__idempotency_config__"

# Headers that must never be replayed verbatim from a cached response.
DEFAULT_HEADER_BLACKLIST: frozenset[str] = frozenset(
    {"set-cookie", "authorization", "www-authenticate"}
)


def idempotent(
    *,
    scope: Scope = "user",
    ttl_seconds: int = 86_400,
    required: bool = False,
) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
    """Mark a route handler as opt-in for idempotency dedup."""
    config = IdempotencyConfig(scope=scope, ttl_seconds=ttl_seconds, required=required)

    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        setattr(func, _ATTR, config)
        return func

    return decorator


def get_config(func: Callable[..., Any] | None) -> IdempotencyConfig | None:
    """Return the idempotency config attached to a route handler, if any."""
    if func is None:
        return None
    return getattr(func, _ATTR, None)
