import uuid
from datetime import datetime

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.sales.repositories.projections import (
    FingerprintContextRepository,
    UserAgeContextRepository,
)
from com.qode.qrew.v1.sales.services.domain.fraud.engine import FraudRuleEngine
from com.qode.qrew.v1.sales.services.domain.fraud.signals.account_age import AccountAgeSignal
from com.qode.qrew.v1.sales.services.domain.fraud.signals.fingerprint_reuse import (
    FingerprintReuseSignal,
)
from com.qode.qrew.v1.sales.services.domain.fraud.signals.ip_velocity import IpVelocitySignal
from com.qode.qrew.v1.sales.services.domain.fraud.signals.time_to_purchase import (
    TimeToPurchaseSignal,
)
from com.qode.qrew.v1.sales.services.domain.fraud.signals.voip_phone import VoipPhoneSignal
from com.qode.qrew.v1.sales.core.config import settings


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


async def build_engine_for_user(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    fingerprint_hash: str | None,
) -> FraudRuleEngine:
    """Assembles the fraud detection engine with projection data pre-loaded for a specific user."""
    redis_client = _shared_redis()

    age_repo = UserAgeContextRepository(session)
    fp_repo = FingerprintContextRepository(session)

    registered_at_lookup: dict[uuid.UUID, datetime] = {}
    fingerprint_lookup: dict[str, int] = {}

    age_ctx = await age_repo.get_by_user_id(user_id)
    if age_ctx is not None:
        registered_at_lookup[user_id] = age_ctx.registered_at

    if fingerprint_hash is not None:
        fp_ctx = await fp_repo.get_by_hash(fingerprint_hash)
        if fp_ctx is not None:
            fingerprint_lookup[fingerprint_hash] = fp_ctx.distinct_user_count

    phone_e164 = age_ctx.phone_e164 if age_ctx is not None else None

    return FraudRuleEngine(
        [
            AccountAgeSignal(registered_at_lookup),
            TimeToPurchaseSignal(registered_at_lookup),
            VoipPhoneSignal(phone_e164),
            IpVelocitySignal(redis_client),
            FingerprintReuseSignal(fingerprint_lookup),
        ]
    )
