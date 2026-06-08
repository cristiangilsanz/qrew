import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import fakeredis.aioredis
import pytest
import pytest_asyncio

from com.qode.qrew.v1.service.core.locking import lock as lock_module
from com.qode.qrew.v1.service.core.payments import CreatedIntent
from com.qode.qrew.v1.service.models.payment import Payment, PaymentStatus
from com.qode.qrew.v1.service.models.reservation import (
    Reservation,
    ReservationStatus,
)
from com.qode.qrew.v1.service.models.ticket import Ticket, TicketState
from com.qode.qrew.v1.service.models.ticket_type import TicketType
from com.qode.qrew.v1.service.services.payment import (
    PaymentError,
    PaymentExpiredError,
    PaymentService,
)


@pytest_asyncio.fixture(autouse=True)
async def _fake_redis_for_locks() -> Any:  # pyright: ignore[reportUnusedFunction]
    fake = fakeredis.aioredis.FakeRedis()
    previous = lock_module._ClientState.client  # pyright: ignore[reportPrivateUsage]
    lock_module._ClientState.client = fake  # pyright: ignore[reportPrivateUsage]
    try:
        yield fake
    finally:
        await fake.aclose()
        lock_module._ClientState.client = previous  # pyright: ignore[reportPrivateUsage]


def _reservation(
    *,
    user_id: uuid.UUID,
    status: ReservationStatus = ReservationStatus.reserved,
    expires_in: timedelta = timedelta(minutes=5),
) -> Reservation:
    res = Reservation(
        id=uuid.uuid4(),
        user_id=user_id,
        event_id=uuid.uuid4(),
        ticket_type_id=uuid.uuid4(),
        quantity=2,
        status=status,
        expires_at=datetime.now(timezone.utc) + expires_in,
    )
    res.created_at = datetime.now(timezone.utc)
    return res


def _tier(reservation: Reservation) -> TicketType:
    return TicketType(
        id=reservation.ticket_type_id,
        event_id=reservation.event_id,
        name="general",
        description=None,
        capacity=100,
        reserved_count=2,
        price_cents=5000,
        currency="EUR",
        position=0,
    )


class _FakeStripe:
    def __init__(self) -> None:
        self.created: list[dict[str, Any]] = []

    async def create_payment_intent(
        self,
        *,
        amount_cents: int,
        currency: str,
        idempotency_key: str,
        metadata: dict[str, str],
    ) -> CreatedIntent:
        self.created.append(
            {
                "amount_cents": amount_cents,
                "currency": currency,
                "idempotency_key": idempotency_key,
                "metadata": metadata,
            }
        )
        return CreatedIntent(
            intent_id=f"pi_{len(self.created)}",
            client_secret="cs_secret_123",
            status="requires_action",
        )

    def verify_webhook(self, payload: bytes, signature: str) -> dict[str, Any]:
        del payload, signature
        return {}


def _service(
    *,
    reservation: Reservation,
    payment: Payment | None = None,
    tickets: list[Ticket] | None = None,
) -> tuple[PaymentService, _FakeStripe, MagicMock]:
    tier = _tier(reservation)
    session = MagicMock()

    async def _flush() -> None:
        return None

    async def _refresh(_obj: Any) -> None:
        return None

    session.flush = AsyncMock(side_effect=_flush)
    session.refresh = AsyncMock(side_effect=_refresh)
    session.add = MagicMock()

    payments_repo = MagicMock()
    inserted: list[Payment] = []
    if payment is not None:
        payments_repo.get_by_reservation_id = AsyncMock(return_value=payment)
    else:
        payments_repo.get_by_reservation_id = AsyncMock(return_value=None)

    async def _insert(new: Payment) -> Payment:
        new.id = uuid.uuid4()
        new.created_at = datetime.now(timezone.utc)
        inserted.append(new)
        return new

    payments_repo.insert = AsyncMock(side_effect=_insert)
    payments_repo.flush = AsyncMock()
    payments_repo.get_by_intent_id = AsyncMock(return_value=payment)

    reservation_repo = MagicMock()
    reservation_repo.get_by_id = AsyncMock(return_value=reservation)
    reservation_repo.list_tickets = AsyncMock(return_value=tickets or [])

    tier_repo = MagicMock()
    tier_repo.get_by_id = AsyncMock(return_value=tier)

    stripe = _FakeStripe()
    audit = MagicMock()
    audit.record = AsyncMock()

    service = PaymentService(
        session, payments_repo, reservation_repo, tier_repo, stripe, audit
    )
    return service, stripe, payments_repo


async def test_initiate_creates_payment_intent() -> None:
    user_id = uuid.uuid4()
    reservation = _reservation(user_id=user_id)
    service, stripe, _ = _service(reservation=reservation)
    payment = await service.initiate(actor_id=user_id, reservation_id=reservation.id)
    assert payment.provider_payment_intent_id == "pi_1"
    assert payment.status == PaymentStatus.requires_action
    assert stripe.created[0]["idempotency_key"] == f"reservation:{reservation.id}"


async def test_initiate_rejects_other_users_reservation() -> None:
    reservation = _reservation(user_id=uuid.uuid4())
    service, *_ = _service(reservation=reservation)
    with pytest.raises(PaymentError, match="not found"):
        await service.initiate(actor_id=uuid.uuid4(), reservation_id=reservation.id)


async def test_initiate_rejects_expired_reservation() -> None:
    user_id = uuid.uuid4()
    reservation = _reservation(user_id=user_id, expires_in=timedelta(seconds=-1))
    service, *_ = _service(reservation=reservation)
    with pytest.raises(PaymentExpiredError):
        await service.initiate(actor_id=user_id, reservation_id=reservation.id)


async def test_initiate_returns_existing_payment_intent() -> None:
    user_id = uuid.uuid4()
    reservation = _reservation(user_id=user_id)
    existing = Payment(
        id=uuid.uuid4(),
        reservation_id=reservation.id,
        provider_payment_intent_id="pi_existing",
        amount_cents=10000,
        currency="EUR",
        status=PaymentStatus.requires_action,
    )
    service, stripe, _ = _service(reservation=reservation, payment=existing)
    payment = await service.initiate(actor_id=user_id, reservation_id=reservation.id)
    assert payment.provider_payment_intent_id == "pi_existing"
    assert not stripe.created


async def test_apply_succeeded_transitions_reservation_and_tickets() -> None:
    user_id = uuid.uuid4()
    reservation = _reservation(user_id=user_id)
    tickets = [
        Ticket(
            id=uuid.uuid4(),
            reservation_id=reservation.id,
            event_id=reservation.event_id,
            ticket_type_id=reservation.ticket_type_id,
            owner_user_id=user_id,
            state=TicketState.reserved,
        )
        for _ in range(2)
    ]
    payment = Payment(
        id=uuid.uuid4(),
        reservation_id=reservation.id,
        provider_payment_intent_id="pi_1",
        amount_cents=10000,
        currency="EUR",
        status=PaymentStatus.requires_action,
    )
    service, _stripe, _ = _service(
        reservation=reservation, payment=payment, tickets=tickets
    )
    await service.apply_succeeded(intent_id="pi_1")
    assert reservation.status == ReservationStatus.paid
    assert all(t.state == TicketState.issued for t in tickets)
    assert payment.status == PaymentStatus.succeeded


async def test_apply_failed_records_failure_and_keeps_reservation() -> None:
    user_id = uuid.uuid4()
    reservation = _reservation(user_id=user_id)
    payment = Payment(
        id=uuid.uuid4(),
        reservation_id=reservation.id,
        provider_payment_intent_id="pi_1",
        amount_cents=10000,
        currency="EUR",
        status=PaymentStatus.requires_action,
    )
    service, *_ = _service(reservation=reservation, payment=payment)
    await service.apply_failed(
        intent_id="pi_1", failure_code="card_declined", failure_message="boom"
    )
    assert payment.status == PaymentStatus.failed
    assert payment.failure_code == "card_declined"
    assert reservation.status == ReservationStatus.reserved


async def test_apply_succeeded_unknown_intent_is_noop() -> None:
    user_id = uuid.uuid4()
    reservation = _reservation(user_id=user_id)
    service, *_ = _service(reservation=reservation, payment=None)
    await service.apply_succeeded(intent_id="pi_unknown")
    assert reservation.status == ReservationStatus.reserved
