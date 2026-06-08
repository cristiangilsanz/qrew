from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.service.models.device.fingerprint import DeviceFingerprint
from com.qode.qrew.v1.service.services.fraud.context import PurchaseContext
from com.qode.qrew.v1.service.services.fraud.signals.base import SignalResult
from com.qode.qrew.v1.service.settings import settings


class FingerprintReuseSignal:
    """Count distinct accounts seen on the same fingerprint in the lookback."""

    name = "fingerprint_reuse"

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def evaluate(self, context: PurchaseContext) -> SignalResult:
        fingerprint = context.device_fingerprint_hash
        if fingerprint is None:
            return SignalResult(name=self.name, score=0, reason="no_fingerprint")
        cutoff = context.now - timedelta(
            hours=settings.fraud_fingerprint_lookback_hours
        )
        result = await self._session.execute(
            select(func.count(func.distinct(DeviceFingerprint.user_id)))
            .where(DeviceFingerprint.fingerprint_hash == fingerprint)
            .where(DeviceFingerprint.seen_at >= cutoff)
        )
        distinct_accounts = int(result.scalar_one() or 0)
        if distinct_accounts > settings.fraud_fingerprint_threshold:
            return SignalResult(
                name=self.name,
                score=settings.fraud_weight_fingerprint_reuse,
                reason=f"distinct_accounts:{distinct_accounts}",
            )
        return SignalResult(name=self.name, score=0, reason=f"ok:{distinct_accounts}")
