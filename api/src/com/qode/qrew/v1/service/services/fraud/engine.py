from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

import structlog

from com.qode.qrew.v1.service.services.fraud.context import PurchaseContext
from com.qode.qrew.v1.service.services.fraud.signals import Signal, SignalResult
from com.qode.qrew.v1.service.settings import settings

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
                {"name": s.name, "score": s.score, "reason": s.reason}
                for s in self.signals
            ],
        }


class FraudRuleEngine:
    """Sums per-signal scores and maps to allow / review / block."""

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
                await logger.awarning(
                    "fraud_signal_failed", signal=signal.name, error=repr(exc)
                )
                continue
            results.append(result)
        total = sum(r.score for r in results)
        decision = self._classify(total)
        await logger.ainfo(
            "fraud.score.computed",
            score=total,
            decision=decision.value,
            signals=[
                {"name": r.name, "score": r.score, "reason": r.reason} for r in results
            ],
        )
        return FraudEvaluation(score=total, decision=decision, signals=results)

    @staticmethod
    def _classify(score: int) -> FraudDecision:
        if score >= settings.fraud_score_block_threshold:
            return FraudDecision.block
        if score >= settings.fraud_score_review_threshold:
            return FraudDecision.review
        return FraudDecision.allow
