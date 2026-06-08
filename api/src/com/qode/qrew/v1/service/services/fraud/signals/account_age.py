from datetime import timedelta

from com.qode.qrew.v1.service.services.fraud.context import PurchaseContext
from com.qode.qrew.v1.service.services.fraud.signals.base import SignalResult
from com.qode.qrew.v1.service.settings import settings


class AccountAgeSignal:
    """Younger accounts score higher; brand-new ones add the most."""

    name = "account_age"

    async def evaluate(self, context: PurchaseContext) -> SignalResult:
        age = context.now - context.user_created_at
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
