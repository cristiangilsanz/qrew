import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from com.qode.qrew.v1.sales.models.reservation import ReservationStatus
from com.qode.qrew.v1.sales.services.application.audit import AuditService


@pytest.fixture
def user_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def event_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def ticket_type_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def audit() -> AuditService:
    mock = AsyncMock(spec=AuditService)
    mock.record = AsyncMock()
    return mock


@pytest.fixture
def now() -> datetime:
    return datetime.now(UTC)


def make_reservation(
    *,
    user_id: uuid.UUID,
    event_id: uuid.UUID,
    ticket_type_id: uuid.UUID,
    status: ReservationStatus = ReservationStatus.reserved,
    quantity: int = 2,
    expires_at: datetime | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        user_id=user_id,
        event_id=event_id,
        ticket_type_id=ticket_type_id,
        quantity=quantity,
        status=status,
        expires_at=expires_at or datetime.now(UTC) + timedelta(minutes=10),
        risk_score=0,
        requires_review=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def make_inventory(
    *,
    ticket_type_id: uuid.UUID,
    event_id: uuid.UUID,
    capacity: int = 100,
    reserved_count: int = 0,
    price_cents: int = 1000,
    currency: str = "EUR",
) -> SimpleNamespace:
    return SimpleNamespace(
        ticket_type_id=ticket_type_id,
        event_id=event_id,
        capacity=capacity,
        reserved_count=reserved_count,
        price_cents=price_cents,
        currency=currency,
    )


def make_event_ctx(
    *,
    event_id: uuid.UUID,
    status: str = "published",
    max_tickets_per_user: int = 10,
    queue_required: bool = False,
    sale_starts_at: datetime | None = None,
    sale_ends_at: datetime | None = None,
) -> SimpleNamespace:
    now = datetime.now(UTC)
    return SimpleNamespace(
        event_id=event_id,
        status=status,
        max_tickets_per_user=max_tickets_per_user,
        queue_required=queue_required,
        sale_starts_at=sale_starts_at or now - timedelta(hours=1),
        sale_ends_at=sale_ends_at or now + timedelta(hours=1),
    )
