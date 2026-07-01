import os

# Must be set before importing any entry service module that calls _load_purpose_keys().
os.environ.setdefault("DEBUG", "true")

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from com.qode.qrew.v1.entry.models.projections import TicketState
from com.qode.qrew.v1.entry.services.application.audit import AuditService


@pytest.fixture
def scanner_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def venue_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def event_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def admin_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def audit() -> AuditService:
    mock = AsyncMock(spec=AuditService)
    mock.record = AsyncMock()
    return mock


def make_scanner(
    *,
    scanner_id: uuid.UUID | None = None,
    venue_id: uuid.UUID | None = None,
    is_active: bool = True,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=scanner_id or uuid.uuid4(),
        venue_id=venue_id or uuid.uuid4(),
        name="Gate 1",
        is_active=is_active,
        last_refreshed_at=None,
    )


def make_ticket_ctx(
    *,
    ticket_id: uuid.UUID,
    event_id: uuid.UUID,
    venue_id: uuid.UUID | None = None,
    owner_user_id: uuid.UUID | None = None,
    state: str = TicketState.issued.value,
) -> SimpleNamespace:
    return SimpleNamespace(
        ticket_id=ticket_id,
        event_id=event_id,
        venue_id=venue_id,
        owner_user_id=owner_user_id or uuid.uuid4(),
        state=state,
    )
