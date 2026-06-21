import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from com.qode.qrew.v1.catalog.models.event import EventStatus
from com.qode.qrew.v1.catalog.models.organisation import OrganisationRole


@pytest.fixture
def actor_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def org_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def venue_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def event_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def ticket_type_id() -> uuid.UUID:
    return uuid.uuid4()


# ── Time helpers ──────────────────────────────────────────────────────────────

def future(*, hours: int = 0, days: int = 0) -> datetime:
    return datetime.now(UTC) + timedelta(hours=hours, days=days)


def past(*, hours: int = 0, days: int = 0) -> datetime:
    return datetime.now(UTC) - timedelta(hours=hours, days=days)


# ── Model factories ───────────────────────────────────────────────────────────

def make_org(*, org_id: uuid.UUID | None = None, slug: str = "acme", name: str = "Acme") -> SimpleNamespace:
    return SimpleNamespace(id=org_id or uuid.uuid4(), slug=slug, name=name, description=None)


def make_venue(*, venue_id: uuid.UUID | None = None, city: str = "Amsterdam") -> SimpleNamespace:
    return SimpleNamespace(
        id=venue_id or uuid.uuid4(),
        name="Stadium",
        city=city,
        country="NL",
        latitude=Decimal("52.370"),
        longitude=Decimal("4.895"),
        geofence_radius_m=200,
        timezone="Europe/Amsterdam",
        description=None,
    )


def make_event(
    *,
    event_id: uuid.UUID | None = None,
    org_id: uuid.UUID | None = None,
    venue_id: uuid.UUID | None = None,
    status: EventStatus = EventStatus.draft,
    name: str = "Concert",
    max_tickets_per_user: int = 4,
) -> SimpleNamespace:
    now = datetime.now(UTC)
    return SimpleNamespace(
        id=event_id or uuid.uuid4(),
        organisation_id=org_id or uuid.uuid4(),
        venue_id=venue_id or uuid.uuid4(),
        name=name,
        description=None,
        starts_at=now + timedelta(days=30),
        ends_at=now + timedelta(days=30, hours=4),
        sale_starts_at=now + timedelta(days=1),
        sale_ends_at=now + timedelta(days=29),
        max_tickets_per_user=max_tickets_per_user,
        status=status,
        organiser_name="Acme",
        venue_city="Amsterdam",
        queue_required=False,
        queue_admit_rate_per_minute=0,
        published_at=None,
        cancelled_at=None,
    )


def make_ticket_type(
    *,
    ticket_type_id: uuid.UUID | None = None,
    event_id: uuid.UUID,
    name: str = "general",
    capacity: int = 500,
    reserved_count: int = 0,
    price_cents: int = 2500,
    currency: str = "EUR",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=ticket_type_id or uuid.uuid4(),
        event_id=event_id,
        name=name,
        description=None,
        capacity=capacity,
        reserved_count=reserved_count,
        price_cents=price_cents,
        currency=currency,
        position=0,
        deleted_at=None,
    )


def make_member(
    *,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    role: OrganisationRole = OrganisationRole.member,
) -> SimpleNamespace:
    return SimpleNamespace(
        organisation_id=org_id,
        user_id=user_id,
        role=role,
    )


# ── Shared redlock helper ─────────────────────────────────────────────────────

def make_redlock_cm() -> MagicMock:
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=None)
    cm.__aexit__ = AsyncMock(return_value=None)
    return cm


def make_fake_settings() -> MagicMock:
    s = MagicMock()
    s.redis_url = "redis://localhost:6379"
    return s
