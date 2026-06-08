import redis.asyncio as aioredis

from com.qode.qrew.v1.service.settings import settings

_KEY_PREFIX = "payments:webhook"


class _ClientState:
    client: aioredis.Redis | None = None  # type: ignore[type-arg]


def _shared_redis() -> aioredis.Redis:  # type: ignore[type-arg]
    if _ClientState.client is None:
        _ClientState.client = aioredis.from_url(  # type: ignore[type-arg]
            settings.redis_url, decode_responses=True
        )
    return _ClientState.client


async def close_webhook_idempotency() -> None:
    if _ClientState.client is not None:
        await _ClientState.client.aclose()
    _ClientState.client = None


async def claim_event(event_id: str) -> bool:
    """Return True if this is the first time we have seen this Stripe event."""
    redis = _shared_redis()
    key = f"{_KEY_PREFIX}:{event_id}"
    result = await redis.set(  # type: ignore[misc]
        key,
        "1",
        ex=settings.payments_webhook_idempotency_ttl_seconds,
        nx=True,
    )
    return bool(result)
