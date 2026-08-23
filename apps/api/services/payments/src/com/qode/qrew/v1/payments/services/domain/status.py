from com.qode.qrew.v1.payments.models.payment import PaymentStatus

_INTENT_STATUS = {
    "succeeded": PaymentStatus.succeeded,
    "processing": PaymentStatus.processing,
    "requires_payment_method": PaymentStatus.requires_action,
    "requires_confirmation": PaymentStatus.requires_action,
    "requires_action": PaymentStatus.requires_action,
    "canceled": PaymentStatus.failed,
}

_TERMINAL = {PaymentStatus.succeeded, PaymentStatus.failed, PaymentStatus.refunded}


def map_intent_status(provider_status: str) -> PaymentStatus:
    """Translate the status of a payment intent into the status this service keeps."""
    return _INTENT_STATUS.get(provider_status, PaymentStatus.requires_action)


def is_terminal(status: PaymentStatus) -> bool:
    """Report whether a status admits no further transition."""
    return status in _TERMINAL
