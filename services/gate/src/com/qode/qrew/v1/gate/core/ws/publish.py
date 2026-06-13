"""Minimal Redis pub/sub publish for gate → WS hub (monolith delivers)."""
import json
from typing import Any

import redis.asyncio as aioredis
import structlog

from com.qode.qrew.v1.gate.settings import settings

logger = structlog.get_logger(__name__)

_REDIS_PREFIX = "ws"


class _State:
    client: aioredis.Redis | None = None  # type: ignore[type-arg]


def _client() -> aioredis.Redis:  # type: ignore[type-arg]
    if _State.client is None:
        _State.client = aioredis.from_url(settings.redis_url, decode_responses=False)  # type: ignore[type-arg]
    return _State.client


async def close_ws_publisher() -> None:
    if _State.client is not None:
        await _State.client.aclose()
    _State.client = None


async def publish(channel_key: str, payload: dict[str, Any]) -> None:
    if not settings.ws_enabled:
        return
    try:
        redis_channel = f"{_REDIS_PREFIX}:{channel_key}"
        await _client().publish(redis_channel, json.dumps(payload))  # type: ignore[misc]
    except Exception as exc:
        await logger.awarning("ws_publish_failed", channel=channel_key, error=repr(exc))
