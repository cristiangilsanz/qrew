from com.qode.qrew.v1.service.services.fraud.context import PurchaseContext
from com.qode.qrew.v1.service.services.fraud.signals.base import SignalResult
from com.qode.qrew.v1.service.settings import settings


class TimeToPurchaseSignal:
    """A first purchase seconds after sign-up looks scripted."""

    name = "time_to_purchase"

    async def evaluate(self, context: PurchaseContext) -> SignalResult:
        seconds = (context.now - context.user_created_at).total_seconds()
        if seconds < 10:
            return SignalResult(
                name=self.name,
                score=settings.fraud_weight_time_to_purchase_immediate,
                reason="under_10_seconds",
            )
        if seconds < 60:
            return SignalResult(
                name=self.name,
                score=settings.fraud_weight_time_to_purchase_fast,
                reason="under_60_seconds",
            )
        return SignalResult(name=self.name, score=0, reason="ok")
