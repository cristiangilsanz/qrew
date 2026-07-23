import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from com.qode.qrew.v1.payments.models.payment import PaymentStatus


@pytest.fixture
def user_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def reservation_id() -> uuid.UUID:
    return uuid.uuid4()


def make_payment(
    *,
    reservation_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    market_assignment_id: uuid.UUID | None = None,
    status: PaymentStatus = PaymentStatus.requires_action,
    intent_id: str | None = "pi_test_123",
    client_secret_ciphertext: bytes | None = b"encrypted",
    amount_cents: int = 2000,
    currency: str = "EUR",
    failure_code: str | None = None,
    failure_message: str | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        reservation_id=reservation_id,
        user_id=user_id or uuid.uuid4(),
        market_assignment_id=market_assignment_id,
        status=status,
        provider_payment_intent_id=intent_id,
        client_secret_ciphertext=client_secret_ciphertext,
        amount_cents=amount_cents,
        currency=currency,
        failure_code=failure_code,
        failure_message=failure_message,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
