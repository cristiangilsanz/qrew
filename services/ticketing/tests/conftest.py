import os
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

os.environ.setdefault("DEBUG", "true")

from com.qode.qrew.v1.ticketing.models.ticket import TicketState  # noqa: E402
from com.qode.qrew.v1.ticketing.services.application.audit import AuditService  # noqa: E402
from com.qode.qrew.v1.ticketing.services.domain.gate import GateInputs  # noqa: E402


@pytest.fixture
def user_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def device_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def audit() -> AuditService:
    mock = AsyncMock(spec=AuditService)
    mock.record = AsyncMock()
    return mock


@pytest.fixture
def now() -> datetime:
    return datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)


def make_ticket(
    *,
    owner_user_id: uuid.UUID,
    state: TicketState = TicketState.issued,
    bound_device_id: uuid.UUID | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        reservation_id=uuid.uuid4(),
        event_id=uuid.uuid4(),
        ticket_type_id=uuid.uuid4(),
        owner_user_id=owner_user_id,
        bound_device_id=bound_device_id,
        state=state,
        state_updated_at=None,
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
    )


_UNSET = object()


def make_device(
    *,
    user_id: uuid.UUID,
    device_id: uuid.UUID,
    attested_at: datetime | None | object = _UNSET,
    revoked_at: datetime | None = None,
) -> SimpleNamespace:
    resolved_attested = datetime.now(UTC) if attested_at is _UNSET else attested_at
    return SimpleNamespace(
        device_id=device_id,
        user_id=user_id,
        attested_at=resolved_attested,
        revoked_at=revoked_at,
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
    )


def make_event_ctx(*, event_id: uuid.UUID) -> SimpleNamespace:
    return SimpleNamespace(
        event_id=event_id,
        venue_id=uuid.uuid4(),
        event_status="published",
        latitude=Decimal("51.5074"),
        longitude=Decimal("-0.1278"),
        geofence_radius_m=500,
        timezone="UTC",
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
    )


def make_gate_inputs(
    *,
    user_id: uuid.UUID,
    device_id: uuid.UUID,
    state: TicketState = TicketState.issued,
    bound_device_id: uuid.UUID | None = None,
) -> GateInputs:
    ticket = make_ticket(owner_user_id=user_id, state=state, bound_device_id=bound_device_id)
    return GateInputs(
        ticket=ticket,  # type: ignore[arg-type]
        event_ctx=make_event_ctx(event_id=ticket.event_id),  # type: ignore[arg-type]
        device_ctx=make_device(user_id=user_id, device_id=device_id),  # type: ignore[arg-type]
    )
