from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol

import structlog

from com.qode.qrew.v1.sales.services.fraud.context import PurchaseContext
from com.qode.qrew.v1.sales.services.fraud.signals.base import SignalResult
from com.qode.qrew.v1.sales.core.config import settings

logger = structlog.get_logger(__name__)


class FraudDecision(StrEnum):
    allow = "allow"
    review = "review"
    block = "block"


@dataclass(frozen=True)
class FraudEvaluation:
    score: int
    decision: FraudDecision
    signals: list[SignalResult]

    def to_payload(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "decision": self.decision.value,
            "signals": [
                {"name": s.name, "score": s.score, "reason": s.reason} for s in self.signals
            ],
        }


class Signal(Protocol):
    name: str

    async def evaluate(self, context: PurchaseContext) -> SignalResult: ...


class FraudRuleEngine:
    def __init__(self, signals: Sequence[Signal]) -> None:
        self._signals = list(signals)

    async def evaluate(self, context: PurchaseContext) -> FraudEvaluation:
        if not settings.fraud_signals_enabled:
            return FraudEvaluation(score=0, decision=FraudDecision.allow, signals=[])
        results: list[SignalResult] = []
        for signal in self._signals:
            try:
                result = await signal.evaluate(context)
            except Exception as exc:
                await logger.awarning("fraud_signal_failed", signal=signal.name, error=repr(exc))
                continue
            results.append(result)
        total = sum(r.score for r in results)
        decision = self._classify(total)
        await logger.ainfo(
            "fraud.score.computed",
            score=total,
            decision=decision.value,
        )
        return FraudEvaluation(score=total, decision=decision, signals=results)

    @staticmethod
    def _classify(score: int) -> FraudDecision:
        if score >= settings.fraud_score_block_threshold:
            return FraudDecision.block
        if score >= settings.fraud_score_review_threshold:
            return FraudDecision.review
        return FraudDecision.allow
