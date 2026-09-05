# provides shared pytest fixtures
import contextlib
import pathlib
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import fakeredis.aioredis
import jwt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from com.qode.qrew.v1.entry.core.config import settings

settings.debug = True
settings.internal_api_key = "test-key"
settings.idempotency_enabled = False
settings.nats_url = ""
settings.ratelimit_enabled = False
settings.ticket_qr_audience = "qrew.scan"
settings.entry_replay_grace_seconds = 10

from com.qode.qrew.v1.entry.app import app  # noqa: E402
from com.qode.qrew.v1.entry.core.database import get_db  # noqa: E402
from com.qode.qrew.v1.entry.core.dependencies import get_redis  # noqa: E402
from com.qode.qrew.v1.entry.core.principals import _KEYS, ALGORITHM  # noqa: E402
from com.qode.qrew.v1.entry.core.utils.jwt import create_scanner_token  # noqa: E402
from com.qode.qrew.v1.entry.models.projections import TicketContext  # noqa: E402
from com.qode.qrew.v1.entry.models.scanner import Scanner  # noqa: E402
from com.qode.qrew.v1.entry.services.application.catalog import (  # noqa: E402
    EventMembership,
)

try:
    from testcontainers.postgres import PostgresContainer

    _DOCKER_AVAILABLE = True
except Exception:
    _DOCKER_AVAILABLE = False


# provides postgres container
@pytest.fixture(scope="session")
def postgres_container():
    if not _DOCKER_AVAILABLE:
        pytest.skip("Docker not available")
    try:
        with PostgresContainer("postgres:16-alpine") as pg:
            yield pg
    except Exception as exc:
        pytest.skip(f"Docker not available: {exc}")


# provides db url
@pytest.fixture(scope="session")
def db_url(postgres_container):
    return postgres_container.get_connection_url().replace("psycopg2", "asyncpg")


# provides run migrations
@pytest.fixture(scope="session", autouse=True)
def run_migrations(postgres_container, db_url):

    from alembic import command as alembic_command
    from alembic.config import Config

    settings.database_url = db_url
    alembic_ini = str(pathlib.Path(__file__).parents[2] / "alembic.ini")
    cfg = Config(alembic_ini)
    cfg.set_main_option("sqlalchemy.url", db_url)
    alembic_command.upgrade(cfg, "head")


# provides session factory
@pytest.fixture(scope="session")
def session_factory(db_url):
    engine = create_async_engine(db_url, pool_pre_ping=True)
    return async_sessionmaker(engine, expire_on_commit=False)


# provides db
@pytest.fixture
async def db(session_factory) -> AsyncGenerator[AsyncSession, None]:
    async with session_factory() as session:
        yield session
        await session.commit()


# provides fake redis
@pytest.fixture
def fake_redis():
    return fakeredis.aioredis.FakeRedis()


# provides client
@pytest.fixture
async def client(session_factory, fake_redis) -> AsyncGenerator[AsyncClient, None]:
    # handles override get db
    async def _override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_redis] = lambda: fake_redis

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c

    app.dependency_overrides.clear()


# handles make access token
def make_access_token(user_id: uuid.UUID, *, is_admin: bool = False) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": str(user_id),
            "type": "access",
            "adm": is_admin,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(hours=1)).timestamp()),
        },
        _KEYS["access"].private_pem,
        algorithm=ALGORITHM,
        headers={"kid": _KEYS["access"].kid},
    )


# handles make ticket qr jwt
def make_ticket_qr_jwt(
    ticket_id: uuid.UUID,
    event_id: uuid.UUID,
    venue_id: uuid.UUID,
    *,
    jti: str | None = None,
) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "ticket_id": str(ticket_id),
            "event_id": str(event_id),
            "venue_id": str(venue_id),
            "jti": jti or str(uuid.uuid4()),
            "aud": settings.ticket_qr_audience,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=20)).timestamp()),
        },
        _KEYS["ticket_qr"].private_pem,
        algorithm="ES256",
        headers={"kid": _KEYS["ticket_qr"].kid},
    )


# handles make scanner token
def make_scanner_token(
    scanner_id: uuid.UUID,
    venue_id: uuid.UUID,
    event_id: uuid.UUID,
) -> str:
    from datetime import date as date_type

    return create_scanner_token(
        scanner_id, venue_id, event_id, date_type.today().isoformat()
    )


# handles noop redlock
@asynccontextmanager
async def _noop_redlock(*args, **kwargs):
    yield


# handles noop ticketing use
async def _noop_ticketing_use(*args, **kwargs) -> None:
    return None


# a principal comes from the token, not from a table of another service
def make_principal(*, is_admin: bool = False) -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4(), is_admin=is_admin)


# answers the catalog membership question without reaching catalog
@contextlib.contextmanager
def membership(
    *,
    event_exists: bool = True,
    is_member: bool = True,
    venue_id: uuid.UUID | None = None,
):
    import com.qode.qrew.v1.entry.core.dependencies as deps

    # handles fetch
    async def _fetch(
        _session: object, _event_id: uuid.UUID, _user_id: uuid.UUID
    ) -> EventMembership:
        return EventMembership(
            event_exists=event_exists,
            is_member=is_member,
            venue_id=venue_id or uuid.uuid4(),
        )

    original = deps.fetch_event_membership
    deps.fetch_event_membership = _fetch
    try:
        yield
    finally:
        deps.fetch_event_membership = original


# handles seed scanner
async def seed_scanner(
    db: AsyncSession, *, created_by: uuid.UUID, venue_id: uuid.UUID
) -> Scanner:
    scanner = Scanner(
        id=uuid.uuid4(),
        name="Test Gate",
        venue_id=venue_id,
        created_by=created_by,
        is_active=True,
    )
    db.add(scanner)
    await db.commit()
    await db.refresh(scanner)
    return scanner


# handles seed ticket context
async def seed_ticket_context(
    db: AsyncSession,
    *,
    event_id: uuid.UUID,
    venue_id: uuid.UUID,
    owner_user_id: uuid.UUID,
    state: str = "issued",
) -> TicketContext:
    tc = TicketContext(
        ticket_id=uuid.uuid4(),
        event_id=event_id,
        venue_id=venue_id,
        owner_user_id=owner_user_id,
        bound_device_id=None,
        state=state,
    )
    db.add(tc)
    await db.commit()
    await db.refresh(tc)
    return tc
