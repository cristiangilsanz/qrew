# talks to stripe to create payment intents and verify webhooks
from dataclasses import dataclass
from typing import Any, Protocol, cast

import anyio
import stripe  # type: ignore[import-not-found]

from com.qode.qrew.v1.payments.core.config import settings


@dataclass(frozen=True)
class CreatedIntent:
    intent_id: str
    client_secret: str
    status: str


class StripeClient(Protocol):
    # creates a payment intent for the given amount
    async def create_payment_intent(
        self,
        *,
        amount_cents: int,
        currency: str,
        idempotency_key: str,
        metadata: dict[str, str],
    ) -> CreatedIntent: ...

    # verifies a webhook signature and returns its event
    async def verify_webhook(self, payload: bytes, signature: str) -> dict[str, Any]: ...


class StripeRealClient:
    # configures the stripe sdk with the service credentials
    def __init__(self) -> None:
        stripe.api_key = settings.stripe_secret_key
        stripe.api_version = settings.stripe_api_version

    # creates a payment intent through the stripe api
    async def create_payment_intent(
        self,
        *,
        amount_cents: int,
        currency: str,
        idempotency_key: str,
        metadata: dict[str, str],
    ) -> CreatedIntent:
        intent: Any = await anyio.to_thread.run_sync(  # type: ignore[misc]
            lambda: stripe.PaymentIntent.create(
                amount=amount_cents,
                currency=currency.lower(),
                automatic_payment_methods={"enabled": True},
                payment_method_options={"card": {"request_three_d_secure": "any"}},
                metadata=metadata,
                idempotency_key=idempotency_key,
            )
        )
        return CreatedIntent(
            intent_id=cast("str", intent.id),  # type: ignore[reportUnknownMemberType]
            client_secret=cast("str", intent.client_secret or ""),  # type: ignore[reportUnknownMemberType]
            status=cast("str", intent.status),  # type: ignore[reportUnknownMemberType]
        )

    # verifies the webhook signature and parses the event payload
    async def verify_webhook(self, payload: bytes, signature: str) -> dict[str, Any]:
        import json

        await anyio.to_thread.run_sync(  # type: ignore[misc]
            lambda: stripe.Webhook.construct_event(  # type: ignore[no-untyped-call]
                payload=payload,
                sig_header=signature,
                secret=settings.stripe_webhook_signing_secret,
            )
        )
        return cast("dict[str, Any]", json.loads(payload))
