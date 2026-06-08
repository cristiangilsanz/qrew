import time
import uuid

import redis.asyncio as aioredis
import structlog

from com.qode.qrew.v1.service.services.fraud.context import PurchaseContext
from com.qode.qrew.v1.service.services.fraud.signals.base import SignalResult
from com.qode.qrew.v1.service.settings import settings

logger = structlog.get_logger(__name__)

_KEY_PREFIX = "fraud:ip:velocity"


class IpVelocitySignal:
    """Count reservation attempts per IP over a sliding window."""

    name = "ip_velocity"

    def __init__(self, redis_client: aioredis.Redis) -> None:  # type: ignore[type-arg]
        self._redis = redis_client

    async def evaluate(self, context: PurchaseContext) -> SignalResult:
        ip = context.ip_address
        if ip is None:
            return SignalResult(name=self.name, score=0, reason="no_ip")
        key = f"{_KEY_PREFIX}:{ip}"
        window_ms = settings.fraud_ip_velocity_window_seconds * 1000
        now_ms = int(time.time() * 1000)
        try:
            await self._redis.zremrangebyscore(key, 0, now_ms - window_ms)  # type: ignore[misc]
            await self._redis.zadd(key, {f"{now_ms}-{uuid.uuid4().hex}": now_ms})  # type: ignore[misc]
            await self._redis.pexpire(key, window_ms * 2)  # type: ignore[misc]
            count = int(await self._redis.zcard(key))  # type: ignore[misc]
        except aioredis.RedisError as exc:
            await logger.awarning("ip_velocity_unavailable", error=repr(exc))
            return SignalResult(name=self.name, score=0, reason="redis_unavailable")
        if count > settings.fraud_ip_velocity_threshold:
            return SignalResult(
                name=self.name,
                score=settings.fraud_weight_ip_velocity,
                reason=f"observed:{count}",
            )
        return SignalResult(name=self.name, score=0, reason=f"ok:{count}")
