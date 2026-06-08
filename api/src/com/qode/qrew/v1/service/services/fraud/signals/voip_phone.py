from com.qode.qrew.v1.service.services.fraud.context import PurchaseContext
from com.qode.qrew.v1.service.services.fraud.signals.base import SignalResult
from com.qode.qrew.v1.service.settings import settings


class VoipPhoneSignal:
    """Phone numbers from known disposable/VoIP carriers add risk."""

    name = "voip_phone"

    async def evaluate(self, context: PurchaseContext) -> SignalResult:
        phone = context.phone_number
        if phone is None:
            return SignalResult(name=self.name, score=0, reason="no_phone")
        for prefix in settings.fraud_voip_phone_prefixes:
            if phone.startswith(prefix):
                return SignalResult(
                    name=self.name,
                    score=settings.fraud_weight_voip_phone,
                    reason=f"voip_prefix:{prefix}",
                )
        return SignalResult(name=self.name, score=0, reason="ok")
