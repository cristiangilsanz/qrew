# maps stripe payment intent statuses onto the service's own payment status
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


# maps a stripe intent status onto a payment status
def map_intent_status(provider_status: str) -> PaymentStatus:
    return _INTENT_STATUS.get(provider_status, PaymentStatus.requires_action)


# checks whether a payment status is final
def is_terminal(status: PaymentStatus) -> bool:
    return status in _TERMINAL
