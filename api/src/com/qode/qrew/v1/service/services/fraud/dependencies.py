import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.service.services.fraud.engine import FraudRuleEngine
from com.qode.qrew.v1.service.services.fraud.signals import (
    AccountAgeSignal,
    FingerprintReuseSignal,
    IpVelocitySignal,
    TimeToPurchaseSignal,
    VoipPhoneSignal,
)
from com.qode.qrew.v1.service.settings import settings


class _ClientState:
    client: aioredis.Redis | None = None  # type: ignore[type-arg]


def _shared_redis() -> aioredis.Redis:  # type: ignore[type-arg]
    if _ClientState.client is None:
        _ClientState.client = aioredis.from_url(  # type: ignore[type-arg]
            settings.redis_url, decode_responses=True
        )
    return _ClientState.client


async def close_fraud() -> None:
    if _ClientState.client is not None:
        await _ClientState.client.aclose()
    _ClientState.client = None


def build_engine(session: AsyncSession) -> FraudRuleEngine:
    """Compose the default engine; reuses the shared Redis client and DB session."""
    redis_client = _shared_redis()
    return FraudRuleEngine(
        [
            AccountAgeSignal(),
            VoipPhoneSignal(),
            TimeToPurchaseSignal(),
            IpVelocitySignal(redis_client),
            FingerprintReuseSignal(session),
        ]
    )
