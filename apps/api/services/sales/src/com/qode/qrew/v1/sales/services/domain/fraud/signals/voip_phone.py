from typing import cast

import structlog

import httpx

from com.qode.qrew.v1.sales.core.config import settings
from com.qode.qrew.v1.sales.services.domain.fraud.context import PurchaseContext
from com.qode.qrew.v1.sales.services.domain.fraud.signals.base import SignalResult

logger = structlog.get_logger(__name__)

_VOIP_LINE_TYPES = {"voip", "toll-free"}
_TWILIO_LOOKUP_URL = "https://lookups.twilio.com/v2/PhoneNumbers/{number}"


class VoipPhoneSignal:
    """Score a purchase attempt based on whether the user's phone is a VoIP/throwaway number."""

    name = "voip_phone"

    def __init__(self, phone_e164: str | None) -> None:
        self._phone = phone_e164

    async def evaluate(self, context: PurchaseContext) -> SignalResult:
        if not self._phone:
            return SignalResult(name=self.name, score=0, reason="no_phone")
        if not settings.twilio_account_sid or not settings.twilio_auth_token:
            return SignalResult(name=self.name, score=0, reason="twilio_not_configured")

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    _TWILIO_LOOKUP_URL.format(number=self._phone),
                    params={"Fields": "line_type_intelligence"},
                    auth=(settings.twilio_account_sid, settings.twilio_auth_token),
                )
            resp.raise_for_status()
            data: dict[str, object] = resp.json()
            raw_lti: object = data.get("line_type_intelligence")
            lti = cast("dict[str, object]", raw_lti) if isinstance(raw_lti, dict) else {}
            line_type: str = str(lti.get("type") or "")
        except Exception as exc:
            await logger.awarning("voip_signal.lookup_failed", error=repr(exc))
            return SignalResult(name=self.name, score=0, reason="lookup_failed")

        if line_type in _VOIP_LINE_TYPES:
            return SignalResult(
                name=self.name,
                score=settings.fraud_weight_voip_phone,
                reason=f"voip_carrier:{line_type}",
            )
        return SignalResult(name=self.name, score=0, reason=f"carrier:{line_type or 'unknown'}")
