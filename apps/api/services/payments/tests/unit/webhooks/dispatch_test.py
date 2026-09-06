# covers how a verified stripe webhook is routed onto the payment service
from typing import Any

import pytest

from com.qode.qrew.v1.payments.services.application.webhooks.dispatch import (
    dispatch_webhook_event,
    payment_intent_id_for,
    read_dict,
    read_int,
    read_str,
)


class _SpyService:
    # records every call the dispatcher makes
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    # records a settled payment
    async def apply_succeeded(self, **kwargs: Any) -> None:
        self.calls.append(("succeeded", kwargs))

    # records a failed payment
    async def apply_failed(self, **kwargs: Any) -> None:
        self.calls.append(("failed", kwargs))

    # records a payment still in flight
    async def update_intermediate(self, **kwargs: Any) -> None:
        self.calls.append(("intermediate", kwargs))

    # records a refund
    async def apply_refund(self, **kwargs: Any) -> None:
        self.calls.append(("refund", kwargs))

    # records an opened chargeback
    async def apply_chargeback(self, **kwargs: Any) -> None:
        self.calls.append(("chargeback", kwargs))

    # records a closed chargeback
    async def record_chargeback_closed(self, **kwargs: Any) -> None:
        self.calls.append(("chargeback_closed", kwargs))


# builds a stripe event around one data object
def _event(event_type: str, obj: dict[str, Any]) -> dict[str, Any]:
    return {"type": event_type, "data": {"object": obj}}


class TestFieldReaders:
    # verifies that a string field is read only when it is a string
    def test_reads_a_string_field(self) -> None:
        assert read_str({"a": "x"}, "a") == "x"
        assert read_str({"a": 1}, "a") is None
        assert read_str({}, "a") is None

    # verifies that an object field falls back to an empty object
    def test_reads_an_object_field(self) -> None:
        assert read_dict({"a": {"b": 1}}, "a") == {"b": 1}
        assert read_dict({"a": "x"}, "a") == {}

    # verifies that an integer field is read only when it is an integer
    def test_reads_an_integer_field(self) -> None:
        assert read_int({"a": 5}, "a") == 5
        assert read_int({"a": "5"}, "a") is None


class TestPaymentIntentIdFor:
    # verifies that a charge event names the intent it belongs to
    def test_a_charge_event_names_its_intent(self) -> None:
        assert payment_intent_id_for("charge.refunded", {"payment_intent": "pi_1"}) == "pi_1"

    # verifies that an intent event is identified by its own id
    def test_an_intent_event_uses_its_own_id(self) -> None:
        assert payment_intent_id_for("payment_intent.succeeded", {"id": "pi_1"}) == "pi_1"


class TestDispatchWebhookEvent:
    # verifies that an event naming no intent is ignored
    async def test_an_event_without_an_intent_is_ignored(self) -> None:
        service = _SpyService()
        await dispatch_webhook_event(service, _event("payment_intent.succeeded", {}))  # type: ignore[arg-type]
        assert service.calls == []

    # verifies that an unknown event type is ignored
    async def test_an_unknown_event_type_is_ignored(self) -> None:
        service = _SpyService()
        await dispatch_webhook_event(service, _event("invoice.paid", {"id": "pi_1"}))  # type: ignore[arg-type]
        assert service.calls == []

    # verifies that a settled payment is applied
    async def test_a_settled_payment_is_applied(self) -> None:
        service = _SpyService()
        await dispatch_webhook_event(service, _event("payment_intent.succeeded", {"id": "pi_1"}))  # type: ignore[arg-type]
        assert service.calls == [("succeeded", {"intent_id": "pi_1"})]

    # verifies that a failed payment carries the reason stripe gave
    async def test_a_failed_payment_carries_the_reason(self) -> None:
        service = _SpyService()
        await dispatch_webhook_event(
            service,  # type: ignore[arg-type]
            _event(
                "payment_intent.payment_failed",
                {"id": "pi_1", "last_payment_error": {"code": "card_declined", "message": "No."}},
            ),
        )
        name, kwargs = service.calls[0]
        assert name == "failed"
        assert kwargs["failure_code"] == "card_declined"

    # verifies that a payment still in flight records its stripe status
    @pytest.mark.parametrize(
        "event_type", ["payment_intent.requires_action", "payment_intent.processing"]
    )
    async def test_a_payment_in_flight_records_its_status(self, event_type: str) -> None:
        service = _SpyService()
        await dispatch_webhook_event(
            service,  # type: ignore[arg-type]
            _event(event_type, {"id": "pi_1", "status": "processing"}),
        )
        assert service.calls == [("intermediate", {"intent_id": "pi_1", "status": "processing"})]

    # verifies that a payment in flight without a status is ignored
    async def test_a_payment_in_flight_without_a_status_is_ignored(self) -> None:
        service = _SpyService()
        await dispatch_webhook_event(
            service,  # type: ignore[arg-type]
            _event("payment_intent.processing", {"id": "pi_1"}),
        )
        assert service.calls == []

    # verifies that a refund carries both the refunded and the total amount
    async def test_a_refund_carries_both_amounts(self) -> None:
        service = _SpyService()
        await dispatch_webhook_event(
            service,  # type: ignore[arg-type]
            _event(
                "charge.refunded",
                {"payment_intent": "pi_1", "amount": 2000, "amount_refunded": 500},
            ),
        )
        assert service.calls == [
            ("refund", {"intent_id": "pi_1", "amount_refunded": 500, "amount_total": 2000})
        ]

    # verifies that an opened dispute is applied as a chargeback
    async def test_an_opened_dispute_is_applied(self) -> None:
        service = _SpyService()
        await dispatch_webhook_event(
            service,  # type: ignore[arg-type]
            _event("charge.dispute.created", {"payment_intent": "pi_1"}),
        )
        assert service.calls == [("chargeback", {"intent_id": "pi_1"})]

    # verifies that a closed dispute is recorded
    async def test_a_closed_dispute_is_recorded(self) -> None:
        service = _SpyService()
        await dispatch_webhook_event(
            service,  # type: ignore[arg-type]
            _event("charge.dispute.closed", {"payment_intent": "pi_1"}),
        )
        assert service.calls == [("chargeback_closed", {"intent_id": "pi_1"})]
