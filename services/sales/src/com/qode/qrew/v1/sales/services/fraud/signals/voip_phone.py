from com.qode.qrew.v1.sales.services.fraud.context import PurchaseContext
from com.qode.qrew.v1.sales.services.fraud.signals.base import SignalResult


class VoipPhoneSignal:
    """Heuristic score for known VoIP/throwaway phone number patterns."""

    name = "voip_phone"

    async def evaluate(self, context: PurchaseContext) -> SignalResult:
        return SignalResult(name=self.name, score=0, reason="no_phone_in_sales")
