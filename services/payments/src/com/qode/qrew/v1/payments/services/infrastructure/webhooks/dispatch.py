from typing import Any, cast

import structlog

from com.qode.qrew.v1.payments.services.application.payment import PaymentService

logger = structlog.get_logger(__name__)


def read_str(d: dict[str, Any], key: str) -> str | None:
    value: Any = d.get(key)
    return value if isinstance(value, str) else None


def read_dict(d: dict[str, Any], key: str) -> dict[str, Any]:
    value: Any = d.get(key)
    return cast("dict[str, Any]", value) if isinstance(value, dict) else {}


def read_int(d: dict[str, Any], key: str) -> int | None:
    value: Any = d.get(key)
    return value if isinstance(value, int) else None


def payment_intent_id_for(event_type: str, data_object: dict[str, Any]) -> str | None:
    if event_type.startswith("charge."):
        return read_str(data_object, "payment_intent")
    return read_str(data_object, "id")


async def dispatch_webhook_event(service: PaymentService, event: dict[str, Any]) -> None:
    event_type = read_str(event, "type") or ""
    data_section = read_dict(event, "data")
    data_object = read_dict(data_section, "object")
    intent_id = payment_intent_id_for(event_type, data_object)
    if intent_id is None:
        return
    if event_type == "payment_intent.succeeded":
        await service.apply_succeeded(intent_id=intent_id)
    elif event_type == "payment_intent.payment_failed":
        last_error = read_dict(data_object, "last_payment_error")
        await service.apply_failed(
            intent_id=intent_id,
            failure_code=read_str(last_error, "code"),
            failure_message=read_str(last_error, "message"),
        )
    elif event_type in {
        "payment_intent.requires_action",
        "payment_intent.processing",
    }:
        stripe_status = read_str(data_object, "status")
        if stripe_status is not None:
            await service.update_intermediate(intent_id=intent_id, status=stripe_status)
    elif event_type == "charge.refunded":
        amount = read_int(data_object, "amount") or 0
        amount_refunded = read_int(data_object, "amount_refunded") or 0
        await service.apply_refund(
            intent_id=intent_id,
            amount_refunded=amount_refunded,
            amount_total=amount,
        )
    elif event_type == "charge.dispute.created":
        await service.apply_chargeback(intent_id=intent_id)
    elif event_type == "charge.dispute.closed":
        await service.record_chargeback_closed(intent_id=intent_id)
