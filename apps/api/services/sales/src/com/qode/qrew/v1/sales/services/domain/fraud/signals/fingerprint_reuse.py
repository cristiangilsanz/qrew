# scores a purchase against how many accounts share its device fingerprint
from com.qode.qrew.v1.sales.services.domain.fraud.context import PurchaseContext
from com.qode.qrew.v1.sales.services.domain.fraud.signals.base import SignalResult
from com.qode.qrew.v1.sales.core.config import settings


class FingerprintReuseSignal:
    name = "fingerprint_reuse"

    # stores the lookup of distinct accounts per fingerprint
    def __init__(self, fingerprint_lookup: dict[str, int]) -> None:
        self._lookup = fingerprint_lookup

    # scores a purchase higher the more accounts share its fingerprint
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
