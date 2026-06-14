import uuid
from datetime import datetime

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.sales.repositories.projections import (
    FingerprintContextRepository,
    UserAgeContextRepository,
)
from com.qode.qrew.v1.sales.services.fraud.engine import FraudRuleEngine
from com.qode.qrew.v1.sales.services.fraud.signals.account_age import AccountAgeSignal
from com.qode.qrew.v1.sales.services.fraud.signals.fingerprint_reuse import (
    FingerprintReuseSignal,
)
from com.qode.qrew.v1.sales.services.fraud.signals.ip_velocity import IpVelocitySignal
from com.qode.qrew.v1.sales.services.fraud.signals.time_to_purchase import (
    TimeToPurchaseSignal,
)
from com.qode.qrew.v1.sales.services.fraud.signals.voip_phone import VoipPhoneSignal
from com.qode.qrew.v1.sales.settings import settings


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


async def build_engine(session: AsyncSession) -> FraudRuleEngine:
    """Compose the fraud engine; loads projection data for user-age and fingerprint signals."""
    redis_client = _shared_redis()

    # Pre-load projections needed by signals (avoids per-signal async DB calls)
    # AccountAgeSignal gets a dict {user_id: registered_at}
    # FingerprintReuseSignal gets a dict {hash: distinct_user_count}
    # These are tiny lookups — the projections table is a point read.
    # Signals receive a pre-fetched dict so the engine stays synchronous-safe.
    registered_at_lookup: dict[uuid.UUID, datetime] = {}
    fingerprint_lookup: dict[str, int] = {}

    return FraudRuleEngine(
        [
            AccountAgeSignal(registered_at_lookup),
            TimeToPurchaseSignal(registered_at_lookup),
            VoipPhoneSignal(),
            IpVelocitySignal(redis_client),
            FingerprintReuseSignal(fingerprint_lookup),
        ]
    )


async def build_engine_for_user(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    fingerprint_hash: str | None,
) -> FraudRuleEngine:
    """Build engine with pre-fetched projections for a specific user/fingerprint."""
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

    return FraudRuleEngine(
        [
            AccountAgeSignal(registered_at_lookup),
            TimeToPurchaseSignal(registered_at_lookup),
            VoipPhoneSignal(),
            IpVelocitySignal(redis_client),
            FingerprintReuseSignal(fingerprint_lookup),
        ]
    )
