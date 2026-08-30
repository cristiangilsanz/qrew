# covers the fraud rule engine and the signals it combines
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from com.qode.qrew.v1.sales.core.config import settings
from com.qode.qrew.v1.sales.services.domain.fraud.context import PurchaseContext
from com.qode.qrew.v1.sales.services.domain.fraud.engine import (
    FraudDecision,
    FraudRuleEngine,
)
from com.qode.qrew.v1.sales.services.domain.fraud.signals.base import SignalResult
from com.qode.qrew.v1.sales.services.domain.fraud.signals.ip_velocity import IpVelocitySignal
from com.qode.qrew.v1.sales.services.domain.fraud.signals.time_to_purchase import (
    TimeToPurchaseSignal,
)
from com.qode.qrew.v1.sales.services.domain.fraud.signals import voip_phone
from com.qode.qrew.v1.sales.services.domain.fraud.signals.voip_phone import VoipPhoneSignal

NOW = datetime(2026, 1, 1, tzinfo=UTC)


# builds a purchase context with the given address and fingerprint
def _context(ip: str | None = "203.0.113.1") -> PurchaseContext:
    return PurchaseContext(
        user_id=uuid.uuid4(), ip_address=ip, device_fingerprint_hash=None, now=NOW
    )


class _FixedSignal:
    # stores the name and score the signal always reports
    def __init__(self, name: str, score: int) -> None:
        self.name = name
        self._score = score

    # reports the fixed score
    async def evaluate(self, context: PurchaseContext) -> SignalResult:
        del context
        return SignalResult(name=self.name, score=self._score, reason="fixed")


class _FailingSignal:
    name = "boom"

    # raises so the engine has to survive a broken signal
    async def evaluate(self, context: PurchaseContext) -> SignalResult:
        del context
        raise RuntimeError("signal down")


# builds an http client stand in that answers with the given body or fails
def _client_returning(body: dict[str, object] | None) -> object:
    class _Response:
        # raises when the stand in was told to fail
        def raise_for_status(self) -> None:
            if body is None:
                raise RuntimeError("lookup down")

        # returns the body the stand in was built with
        def json(self) -> dict[str, object]:
            return body or {}

    class _Client:
        # accepts whatever arguments the signal passes
        def __init__(self, *args: object, **kwargs: object) -> None:
            del args, kwargs

        # enters the context manager
        async def __aenter__(self) -> "_Client":
            return self

        # leaves the context manager
        async def __aexit__(self, *args: object) -> None:
            del args

        # answers the lookup with the prepared response
        async def get(self, *args: object, **kwargs: object) -> _Response:
            del args, kwargs
            return _Response()

    return _Client


class _FakeRedis:
    # stores the count the script returns
    def __init__(self, count: int) -> None:
        self._count = count

    # stands in for the increment script
    async def eval(self, *args: object, **kwargs: object) -> int:
        del args, kwargs
        return self._count


class TestFraudRuleEngine:
    # verifies that a quiet purchase is allowed
    async def test_low_score_is_allowed(self) -> None:
        engine = FraudRuleEngine([_FixedSignal("a", 1)])
        evaluation = await engine.evaluate(_context())
        assert evaluation.decision is FraudDecision.allow
        assert evaluation.score == 1

    # verifies that a score over the review threshold asks for review
    async def test_score_over_the_review_threshold_asks_for_review(self) -> None:
        engine = FraudRuleEngine([_FixedSignal("a", settings.fraud_score_review_threshold)])
        assert (await engine.evaluate(_context())).decision is FraudDecision.review

    # verifies that a score over the block threshold blocks
    async def test_score_over_the_block_threshold_blocks(self) -> None:
        engine = FraudRuleEngine([_FixedSignal("a", settings.fraud_score_block_threshold)])
        assert (await engine.evaluate(_context())).decision is FraudDecision.block

    # verifies that a broken signal does not stop the rest
    async def test_a_broken_signal_is_skipped(self) -> None:
        engine = FraudRuleEngine([_FailingSignal(), _FixedSignal("a", 3)])
        evaluation = await engine.evaluate(_context())
        assert evaluation.score == 3
        assert [s.name for s in evaluation.signals] == ["a"]

    # verifies that scoring can be turned off entirely
    async def test_scoring_can_be_disabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(settings, "fraud_signals_enabled", False)
        engine = FraudRuleEngine([_FixedSignal("a", 1000)])
        evaluation = await engine.evaluate(_context())
        assert evaluation.decision is FraudDecision.allow
        assert evaluation.signals == []

    # verifies that an evaluation serialises every signal for the audit trail
    async def test_payload_lists_every_signal(self) -> None:
        engine = FraudRuleEngine([_FixedSignal("a", 1), _FixedSignal("b", 2)])
        payload = (await engine.evaluate(_context())).to_payload()
        assert payload["score"] == 3
        assert [s["name"] for s in payload["signals"]] == ["a", "b"]


class TestIpVelocitySignal:
    # verifies that a purchase without an address scores nothing
    async def test_without_an_address_it_scores_nothing(self) -> None:
        result = await IpVelocitySignal(_FakeRedis(99)).evaluate(_context(ip=None))  # type: ignore[arg-type]
        assert result.score == 0
        assert result.reason == "no_ip"

    # verifies that a count under the threshold scores nothing
    async def test_a_quiet_address_scores_nothing(self) -> None:
        result = await IpVelocitySignal(_FakeRedis(1)).evaluate(_context())  # type: ignore[arg-type]
        assert result.score == 0

    # verifies that a count over the threshold scores
    async def test_a_busy_address_scores(self) -> None:
        busy = settings.fraud_ip_velocity_threshold + 1
        result = await IpVelocitySignal(_FakeRedis(busy)).evaluate(_context())  # type: ignore[arg-type]
        assert result.score == settings.fraud_weight_ip_velocity


class TestTimeToPurchaseSignal:
    # verifies that an unknown user scores nothing
    async def test_an_unknown_user_scores_nothing(self) -> None:
        result = await TimeToPurchaseSignal({}).evaluate(_context())
        assert result.reason == "no_age_data"

    # verifies that a purchase within ten seconds of registering scores highest
    async def test_an_immediate_purchase_scores_highest(self) -> None:
        context = _context()
        lookup = {context.user_id: NOW - timedelta(seconds=2)}
        result = await TimeToPurchaseSignal(lookup).evaluate(context)
        assert result.score == settings.fraud_weight_time_to_purchase_immediate

    # verifies that a purchase within a minute scores lower
    async def test_a_fast_purchase_scores_lower(self) -> None:
        context = _context()
        lookup = {context.user_id: NOW - timedelta(seconds=30)}
        result = await TimeToPurchaseSignal(lookup).evaluate(context)
        assert result.score == settings.fraud_weight_time_to_purchase_fast

    # verifies that a purchase long after registering scores nothing
    async def test_a_settled_account_scores_nothing(self) -> None:
        context = _context()
        lookup = {context.user_id: NOW - timedelta(days=30)}
        assert (await TimeToPurchaseSignal(lookup).evaluate(context)).score == 0


class TestVoipPhoneSignal:
    # verifies that a purchase without a phone number scores nothing
    async def test_without_a_phone_it_scores_nothing(self) -> None:
        result = await VoipPhoneSignal(None).evaluate(_context())
        assert result.reason == "no_phone"

    # verifies that the signal stands down when twilio is not configured
    async def test_without_twilio_credentials_it_stands_down(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "twilio_account_sid", "")
        result = await VoipPhoneSignal("+34600000000").evaluate(_context())
        assert result.reason == "twilio_not_configured"

    # verifies that a failed lookup scores nothing rather than blocking the sale
    async def test_a_failed_lookup_scores_nothing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(settings, "twilio_account_sid", "sid")
        monkeypatch.setattr(settings, "twilio_auth_token", "token")
        monkeypatch.setattr(voip_phone.httpx, "AsyncClient", _client_returning(None))
        result = await VoipPhoneSignal("+34600000000").evaluate(_context())
        assert result.score == 0
        assert result.reason == "lookup_failed"

    # verifies that a voip carrier scores
    async def test_a_voip_carrier_scores(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(settings, "twilio_account_sid", "sid")
        monkeypatch.setattr(settings, "twilio_auth_token", "token")
        monkeypatch.setattr(
            voip_phone.httpx,
            "AsyncClient",
            _client_returning({"line_type_intelligence": {"type": "voip"}}),
        )
        result = await VoipPhoneSignal("+34600000000").evaluate(_context())
        assert result.score == settings.fraud_weight_voip_phone

    # verifies that a mobile carrier scores nothing
    async def test_a_mobile_carrier_scores_nothing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(settings, "twilio_account_sid", "sid")
        monkeypatch.setattr(settings, "twilio_auth_token", "token")
        monkeypatch.setattr(
            voip_phone.httpx,
            "AsyncClient",
            _client_returning({"line_type_intelligence": {"type": "mobile"}}),
        )
        result = await VoipPhoneSignal("+34600000000").evaluate(_context())
        assert result.score == 0
        assert result.reason == "carrier:mobile"
