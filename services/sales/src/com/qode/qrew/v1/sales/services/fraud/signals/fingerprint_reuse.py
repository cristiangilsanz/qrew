from com.qode.qrew.v1.sales.services.fraud.context import PurchaseContext
from com.qode.qrew.v1.sales.services.fraud.signals.base import SignalResult
from com.qode.qrew.v1.sales.settings import settings


class FingerprintReuseSignal:
    """Count distinct accounts seen on the same fingerprint via local projection."""

    name = "fingerprint_reuse"

    def __init__(self, fingerprint_lookup: dict[str, int]) -> None:
        self._lookup = fingerprint_lookup

    async def evaluate(self, context: PurchaseContext) -> SignalResult:
        fingerprint = context.device_fingerprint_hash
        if fingerprint is None:
            return SignalResult(name=self.name, score=0, reason="no_fingerprint")
        distinct_accounts: int = self._lookup.get(fingerprint, 0)
        if distinct_accounts > settings.fraud_fingerprint_threshold:
            return SignalResult(
                name=self.name,
                score=settings.fraud_weight_fingerprint_reuse,
                reason=f"distinct_accounts:{distinct_accounts}",
            )
        return SignalResult(name=self.name, score=0, reason=f"ok:{distinct_accounts}")
