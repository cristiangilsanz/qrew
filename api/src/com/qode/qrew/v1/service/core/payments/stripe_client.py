from dataclasses import dataclass
from typing import Any, Protocol

import stripe
import structlog

from com.qode.qrew.v1.service.settings import settings

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class CreatedIntent:
    intent_id: str
    client_secret: str
    status: str


class StripeClient(Protocol):
    """Narrow seam over Stripe so tests can inject a fake."""

    async def create_payment_intent(
        self,
        *,
        amount_cents: int,
        currency: str,
        idempotency_key: str,
        metadata: dict[str, str],
    ) -> CreatedIntent: ...

    def verify_webhook(self, payload: bytes, signature: str) -> dict[str, Any]: ...


class StripeRealClient:
    """Production implementation backed by the official Stripe SDK."""

    def __init__(self) -> None:
        stripe.api_key = settings.stripe_secret_key
        stripe.api_version = settings.stripe_api_version

    async def create_payment_intent(
        self,
        *,
        amount_cents: int,
        currency: str,
        idempotency_key: str,
        metadata: dict[str, str],
    ) -> CreatedIntent:
        intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency=currency.lower(),
            automatic_payment_methods={"enabled": True},
            metadata=metadata,
            idempotency_key=idempotency_key,
        )
        client_secret = intent.client_secret or ""
        return CreatedIntent(
            intent_id=intent.id, client_secret=client_secret, status=intent.status
        )

    def verify_webhook(self, payload: bytes, signature: str) -> dict[str, Any]:
        event = stripe.Webhook.construct_event(  # type: ignore[no-untyped-call]
            payload=payload,
            sig_header=signature,
            secret=settings.stripe_webhook_signing_secret,
        )
        result: dict[str, Any] = dict(event.to_dict_recursive())  # type: ignore[no-untyped-call]
        return result
