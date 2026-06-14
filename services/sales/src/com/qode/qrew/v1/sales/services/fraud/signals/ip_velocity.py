import redis.asyncio as aioredis

from com.qode.qrew.v1.sales.services.fraud.context import PurchaseContext
from com.qode.qrew.v1.sales.services.fraud.signals.base import SignalResult
from com.qode.qrew.v1.sales.settings import settings

_IP_KEY = "fraud:ip:{ip}:purchases"


class IpVelocitySignal:
    """Score high-volume purchase attempts from a single IP."""

    name = "ip_velocity"

    def __init__(self, redis: aioredis.Redis) -> None:  # type: ignore[type-arg]
        self._redis = redis

    async def evaluate(self, context: PurchaseContext) -> SignalResult:
        ip = context.ip_address
        if ip is None:
            return SignalResult(name=self.name, score=0, reason="no_ip")
        key = _IP_KEY.format(ip=ip)
        count = await self._redis.incr(key)  # type: ignore[misc]
        if count == 1:
            window = settings.fraud_ip_velocity_window_minutes * 60
            await self._redis.expire(key, window)  # type: ignore[misc]
        if int(count) > settings.fraud_ip_velocity_threshold:
            return SignalResult(
                name=self.name,
                score=settings.fraud_weight_ip_velocity,
                reason=f"ip_count:{count}",
            )
        return SignalResult(name=self.name, score=0, reason=f"ok:{count}")
