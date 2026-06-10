import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import fakeredis.aioredis
import pytest_asyncio

from com.qode.qrew.v1.service.core.locking import lock as lock_module
from com.qode.qrew.v1.service.models.audit.audit import AuditAction
from com.qode.qrew.v1.service.models.payment import Payment, PaymentStatus
from com.qode.qrew.v1.service.models.reservation import (
    Reservation,
    ReservationStatus,
)
from com.qode.qrew.v1.service.models.ticket import Ticket, TicketState
from com.qode.qrew.v1.service.models.ticket_type import TicketType
from com.qode.qrew.v1.service.services.payment import PaymentService
from tests.v1.conftest import register_test_tickets


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


def _setup(
    *,
    ticket_states: list[TicketState],
    reservation_status: ReservationStatus = ReservationStatus.paid,
    tier_reserved_count: int = 5,
) -> tuple[PaymentService, MagicMock, Reservation, Payment, list[Ticket], TicketType]:
    user_id = uuid.uuid4()
    reservation = Reservation(
        id=uuid.uuid4(),
        user_id=user_id,
        event_id=uuid.uuid4(),
        ticket_type_id=uuid.uuid4(),
        quantity=len(ticket_states),
        status=reservation_status,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )
    reservation.created_at = datetime.now(timezone.utc)
    tier = TicketType(
        id=reservation.ticket_type_id,
        event_id=reservation.event_id,
        name="general",
        description=None,
        capacity=100,
        reserved_count=tier_reserved_count,
        price_cents=5000,
        currency="EUR",
        position=0,
    )
    tickets = [
        Ticket(
            id=uuid.uuid4(),
            reservation_id=reservation.id,
            event_id=reservation.event_id,
            ticket_type_id=reservation.ticket_type_id,
            owner_user_id=user_id,
            state=state,
        )
        for state in ticket_states
    ]
    register_test_tickets(*tickets)
    payment = Payment(
        id=uuid.uuid4(),
        reservation_id=reservation.id,
        provider_payment_intent_id="pi_1",
        amount_cents=10000,
        currency="EUR",
        status=PaymentStatus.succeeded,
    )

    session = MagicMock()

    async def _flush() -> None:
        return None

    async def _refresh(_obj: Any) -> None:
        return None

    session.flush = AsyncMock(side_effect=_flush)
    session.refresh = AsyncMock(side_effect=_refresh)
    session.add = MagicMock()

    payments_repo = MagicMock()
    payments_repo.get_by_intent_id = AsyncMock(return_value=payment)
    payments_repo.flush = AsyncMock()

    reservation_repo = MagicMock()
    reservation_repo.get_by_id = AsyncMock(return_value=reservation)
    reservation_repo.list_tickets = AsyncMock(return_value=tickets)

    tier_repo = MagicMock()
    tier_repo.get_by_id = AsyncMock(return_value=tier)

    audit = MagicMock()
    audit.record = AsyncMock()

    stripe = MagicMock()
    service = PaymentService(
        session, payments_repo, reservation_repo, tier_repo, stripe, audit
    )
    return service, audit, reservation, payment, tickets, tier


async def test_full_refund_cancels_reservation_and_tickets() -> None:
    service, audit, reservation, payment, tickets, tier = _setup(
        ticket_states=[TicketState.issued, TicketState.issued],
        tier_reserved_count=5,
    )
    await service.apply_refund(
        intent_id="pi_1", amount_refunded=10000, amount_total=10000
    )
    assert reservation.status == ReservationStatus.cancelled
    assert all(t.state == TicketState.cancelled for t in tickets)
    assert payment.status == PaymentStatus.refunded
    assert tier.reserved_count == 3
    audited = {c.kwargs["action"] for c in audit.record.await_args_list}
    assert AuditAction.PAYMENT_REFUNDED in audited


async def test_partial_refund_does_not_flip_state() -> None:
    service, audit, reservation, payment, tickets, _ = _setup(
        ticket_states=[TicketState.issued]
    )
    await service.apply_refund(
        intent_id="pi_1", amount_refunded=2000, amount_total=10000
    )
    assert reservation.status == ReservationStatus.paid
    assert all(t.state == TicketState.issued for t in tickets)
    assert payment.status == PaymentStatus.succeeded
    audited = {c.kwargs["action"] for c in audit.record.await_args_list}
    assert AuditAction.PAYMENT_PARTIAL_REFUND in audited
    assert AuditAction.PAYMENT_REFUNDED not in audited


async def test_chargeback_cancels_immediately() -> None:
    service, audit, reservation, payment, tickets, _ = _setup(
        ticket_states=[TicketState.issued, TicketState.issued]
    )
    await service.apply_chargeback(intent_id="pi_1")
    assert reservation.status == ReservationStatus.cancelled
    assert all(t.state == TicketState.cancelled for t in tickets)
    assert payment.status == PaymentStatus.refunded
    audited = {c.kwargs["action"] for c in audit.record.await_args_list}
    assert AuditAction.CHARGEBACK_OPENED in audited


async def test_chargeback_on_used_ticket_does_not_regress_state() -> None:
    service, audit, reservation, payment, tickets, tier = _setup(
        ticket_states=[TicketState.used, TicketState.issued],
        tier_reserved_count=5,
    )
    await service.apply_chargeback(intent_id="pi_1")
    assert tickets[0].state == TicketState.used
    assert tickets[1].state == TicketState.cancelled
    assert reservation.status == ReservationStatus.cancelled
    assert payment.status == PaymentStatus.refunded
    assert tier.reserved_count == 4
    audited = {c.kwargs["action"] for c in audit.record.await_args_list}
    assert AuditAction.CHARGEBACK_ON_USED_TICKET in audited


async def test_unknown_intent_for_refund_is_noop() -> None:
    service, _audit, _, _, _, _ = _setup(ticket_states=[TicketState.issued])
    service._repo.get_by_intent_id = AsyncMock(return_value=None)  # pyright: ignore[reportPrivateUsage]
    await service.apply_refund(
        intent_id="pi_unknown", amount_refunded=10000, amount_total=10000
    )


async def test_chargeback_closed_records_audit_only() -> None:
    service, audit, _, _, _, _ = _setup(ticket_states=[TicketState.cancelled])
    await service.record_chargeback_closed(intent_id="pi_1")
    audited = {c.kwargs["action"] for c in audit.record.await_args_list}
    assert AuditAction.CHARGEBACK_CLOSED in audited
