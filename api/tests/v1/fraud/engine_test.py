import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import fakeredis.aioredis
import pytest
import pytest_asyncio

from com.qode.qrew.v1.service.services.fraud import (
    FraudDecision,
    FraudRuleEngine,
    PurchaseContext,
)
from com.qode.qrew.v1.service.services.fraud.signals import (
    AccountAgeSignal,
    FingerprintReuseSignal,
    IpVelocitySignal,
    TimeToPurchaseSignal,
    VoipPhoneSignal,
)


@pytest_asyncio.fixture
async def redis_client() -> Any:
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    try:
        yield client
    finally:
        await client.aclose()


def _context(
    *,
    age_minutes: float = 60,
    phone: str | None = None,
    ip: str | None = None,
    fingerprint: str | None = None,
) -> PurchaseContext:
    now = datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc)
    return PurchaseContext(
        user_id=uuid.uuid4(),
        user_created_at=now - timedelta(minutes=age_minutes),
        phone_number=phone,
        ip_address=ip,
        device_fingerprint_hash=fingerprint,
        now=now,
    )


async def test_account_age_brand_new_scores_high() -> None:
    signal = AccountAgeSignal()
    result = await signal.evaluate(_context(age_minutes=1))
    assert result.score >= 40


async def test_account_age_young_scores_medium() -> None:
    signal = AccountAgeSignal()
    result = await signal.evaluate(_context(age_minutes=30))
    assert result.score == 20


async def test_account_age_mature_is_zero() -> None:
    signal = AccountAgeSignal()
    result = await signal.evaluate(_context(age_minutes=600))
    assert result.score == 0


async def test_voip_phone_recognises_known_prefix() -> None:
    signal = VoipPhoneSignal()
    result = await signal.evaluate(_context(phone="+18445550199"))
    assert result.score == 25


async def test_voip_phone_unknown_is_zero() -> None:
    signal = VoipPhoneSignal()
    result = await signal.evaluate(_context(phone="+34666555444"))
    assert result.score == 0


async def test_time_to_purchase_under_10s_scores_max() -> None:
    signal = TimeToPurchaseSignal()
    now = datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc)
    ctx = PurchaseContext(
        user_id=uuid.uuid4(),
        user_created_at=now - timedelta(seconds=5),
        phone_number=None,
        ip_address=None,
        device_fingerprint_hash=None,
        now=now,
    )
    result = await signal.evaluate(ctx)
    assert result.score == 50


async def test_ip_velocity_under_threshold_is_zero(redis_client: Any) -> None:
    signal = IpVelocitySignal(redis_client)
    result = await signal.evaluate(_context(ip="1.2.3.4"))
    assert result.score == 0


async def test_ip_velocity_over_threshold_scores(redis_client: Any) -> None:
    signal = IpVelocitySignal(redis_client)
    ip = "1.2.3.4"
    for _ in range(12):
        await signal.evaluate(_context(ip=ip))
    final = await signal.evaluate(_context(ip=ip))
    assert final.score == 35


async def test_fingerprint_reuse_counts_distinct_users() -> None:
    session = MagicMock()
    fake_result = MagicMock()
    fake_result.scalar_one.return_value = 3
    session.execute = AsyncMock(return_value=fake_result)
    signal = FingerprintReuseSignal(session)
    result = await signal.evaluate(_context(fingerprint="abc"))
    assert result.score == 30


async def test_fingerprint_reuse_below_threshold_is_zero() -> None:
    session = MagicMock()
    fake_result = MagicMock()
    fake_result.scalar_one.return_value = 1
    session.execute = AsyncMock(return_value=fake_result)
    signal = FingerprintReuseSignal(session)
    result = await signal.evaluate(_context(fingerprint="abc"))
    assert result.score == 0


class _FixedSignal:
    def __init__(self, name: str, score: int) -> None:
        self.name = name
        self._score = score

    async def evaluate(self, context: PurchaseContext) -> Any:
        from com.qode.qrew.v1.service.services.fraud.signals import SignalResult

        del context
        return SignalResult(name=self.name, score=self._score, reason="fixed")


async def test_engine_classifies_block_at_or_above_threshold() -> None:
    engine = FraudRuleEngine([_FixedSignal("a", 40), _FixedSignal("b", 30)])
    evaluation = await engine.evaluate(_context())
    assert evaluation.score == 70
    assert evaluation.decision == FraudDecision.block


async def test_engine_classifies_review_in_band() -> None:
    engine = FraudRuleEngine([_FixedSignal("a", 50)])
    evaluation = await engine.evaluate(_context())
    assert evaluation.decision == FraudDecision.review


async def test_engine_classifies_allow_below_review() -> None:
    engine = FraudRuleEngine([_FixedSignal("a", 10)])
    evaluation = await engine.evaluate(_context())
    assert evaluation.decision == FraudDecision.allow


async def test_engine_returns_allow_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from com.qode.qrew.v1.service.settings import settings

    monkeypatch.setattr(settings, "fraud_signals_enabled", False)
    engine = FraudRuleEngine([_FixedSignal("a", 100)])
    evaluation = await engine.evaluate(_context())
    assert evaluation.decision == FraudDecision.allow
    assert evaluation.score == 0
