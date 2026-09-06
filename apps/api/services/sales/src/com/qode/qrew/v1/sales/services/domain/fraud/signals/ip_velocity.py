# scores a purchase against how many recent purchases its ip address made
import redis.asyncio as aioredis

from com.qode.qrew.v1.sales.services.domain.fraud.context import PurchaseContext
from com.qode.qrew.v1.sales.services.domain.fraud.signals.base import SignalResult
from com.qode.qrew.v1.sales.core.config import settings

_IP_KEY = "fraud:ip:{ip}:purchases"

_INCR_WITH_TTL = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return count
"""


class IpVelocitySignal:
    name = "ip_velocity"

    # stores the redis client the signal counts through
    def __init__(self, redis: aioredis.Redis) -> None:  # type: ignore[type-arg]
        self._redis = redis

    # scores a purchase higher the more purchases its ip made in the window
    async def evaluate(self, context: PurchaseContext) -> SignalResult:
        ip = context.ip_address
        if ip is None:
            return SignalResult(name=self.name, score=0, reason="no_ip")
        key = _IP_KEY.format(ip=ip)
        window = settings.fraud_ip_velocity_window_minutes * 60
        count: int = int(await self._redis.eval(_INCR_WITH_TTL, 1, key, str(window)))  # type: ignore[misc]
        if count > settings.fraud_ip_velocity_threshold:
            return SignalResult(
                name=self.name,
                score=settings.fraud_weight_ip_velocity,
                reason=f"ip_count:{count}",
            )
        return SignalResult(name=self.name, score=0, reason=f"ok:{count}")
