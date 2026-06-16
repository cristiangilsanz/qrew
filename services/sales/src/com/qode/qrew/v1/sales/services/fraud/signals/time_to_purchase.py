import uuid
from datetime import datetime

from com.qode.qrew.v1.sales.services.fraud.context import PurchaseContext
from com.qode.qrew.v1.sales.services.fraud.signals.base import SignalResult
from com.qode.qrew.v1.sales.core.config import settings


class TimeToPurchaseSignal:
    """A first purchase seconds after sign-up looks scripted."""

    name = "time_to_purchase"

    def __init__(self, registered_at_lookup: dict[uuid.UUID, datetime]) -> None:
        self._lookup = registered_at_lookup

    async def evaluate(self, context: PurchaseContext) -> SignalResult:
        registered_at = self._lookup.get(context.user_id)
        if registered_at is None:
            return SignalResult(name=self.name, score=0, reason="no_age_data")
        seconds = (context.now - registered_at).total_seconds()
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
