import uuid
from datetime import datetime, timedelta

from com.qode.qrew.v1.sales.services.domain.fraud.context import PurchaseContext
from com.qode.qrew.v1.sales.services.domain.fraud.signals.base import SignalResult
from com.qode.qrew.v1.sales.core.config import settings


class AccountAgeSignal:
    """Scores fraud risk based on how recently the account was created, with newer accounts receiving higher scores."""

    name = "account_age"

    def __init__(self, registered_at_lookup: dict[uuid.UUID, datetime]) -> None:
        self._lookup = registered_at_lookup

    async def evaluate(self, context: PurchaseContext) -> SignalResult:
        registered_at = self._lookup.get(context.user_id)
        if registered_at is None:
            return SignalResult(name=self.name, score=0, reason="unknown_age")
        age = context.now - registered_at
        if age < timedelta(minutes=10):
            return SignalResult(
                name=self.name,
                score=settings.fraud_weight_account_age_recent,
                reason="account_younger_than_10_minutes",
            )
        if age < timedelta(hours=1):
            return SignalResult(
                name=self.name,
                score=settings.fraud_weight_account_age_young,
                reason="account_younger_than_1_hour",
            )
        return SignalResult(name=self.name, score=0, reason="ok")
