import os
import pathlib
import time
import uuid as _uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import fakeredis
import fakeredis.aioredis
import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("IDEMPOTENCY_ENABLED", "false")
os.environ.setdefault("RATELIMIT_ENABLED", "false")
os.environ.setdefault("NATS_URL", "")
os.environ.setdefault("OTEL_ENABLED", "false")
os.environ.setdefault("FRAUD_SIGNALS_ENABLED", "false")


def _get_test_db_url() -> str | None:
    explicit = os.environ.get("SALES_TEST_DB_URL") or os.environ.get("DATABASE_URL")
    if explicit:
        for old, new in (
            ("postgresql+psycopg2://", "postgresql+asyncpg://"),
            ("postgresql://", "postgresql+asyncpg://"),
        ):
            if explicit.startswith(old):
                return explicit.replace(old, new, 1)
        return explicit
    try:
        from testcontainers.postgres import PostgresContainer

        _pg = PostgresContainer("postgres:16-alpine")
        _pg.start()
        url: str = _pg.get_connection_url()
        for old, new in (
            ("postgresql+psycopg2://", "postgresql+asyncpg://"),
            ("postgresql://", "postgresql+asyncpg://"),
        ):
            if url.startswith(old):
                url = url.replace(old, new, 1)
                break
        return url
    except Exception:
        return None


@pytest.fixture(scope="session")
def test_db_url() -> str:
    url = _get_test_db_url()
    if url is None:
        pytest.skip(
            "Integration tests require Postgres. "
            "Set SALES_TEST_DB_URL or start Docker (testcontainers)."
        )
    return url


@pytest.fixture(scope="session", autouse=True)
def setup_test_infrastructure(test_db_url: str) -> None:
    from com.qode.qrew.v1.sales.core.config import settings
    import com.qode.qrew.v1.sales.core.database as db_module

    settings.database_url = test_db_url
    settings.debug = True
    settings.idempotency_enabled = False
    settings.nats_url = ""
    settings.fraud_signals_enabled = False
    settings.internal_api_key = "test-internal-key"
    settings.ratelimit_enabled = False

    new_engine = create_async_engine(test_db_url, pool_pre_ping=True)
    db_module.engine = new_engine
    db_module.AsyncSessionLocal = async_sessionmaker(
        new_engine, class_=AsyncSession, expire_on_commit=False
    )

    alembic_ini = str(pathlib.Path(__file__).parents[2] / "alembic.ini")
    from alembic.config import Config
    from alembic import command as alembic_command

    cfg = Config(alembic_ini)
    cfg.set_main_option("sqlalchemy.url", test_db_url)
    alembic_command.upgrade(cfg, "head")


@pytest.fixture(scope="session")
def fake_redis_server() -> fakeredis.FakeServer:
    return fakeredis.FakeServer()


@pytest.fixture(scope="session", autouse=True)
def patch_redis_globally(fake_redis_server: fakeredis.FakeServer):
    def make_fake(url: str, **kwargs: object) -> fakeredis.aioredis.FakeRedis:
        decode = bool(kwargs.get("decode_responses", False))
        return fakeredis.aioredis.FakeRedis(server=fake_redis_server, decode_responses=decode)

    with patch("redis.asyncio.from_url", side_effect=make_fake):
        yield


@pytest.fixture(scope="session")
def test_session_factory(setup_test_infrastructure: None) -> async_sessionmaker[AsyncSession]:
    import com.qode.qrew.v1.sales.core.database as db_module

    return db_module.AsyncSessionLocal


@pytest_asyncio.fixture
async def client(
    setup_test_infrastructure: None, patch_redis_globally: None
) -> AsyncGenerator[httpx.AsyncClient, None]:
    from com.qode.qrew.v1.sales.app import app
    from com.qode.qrew.v1.sales.services.application.queue import storage as queue_storage
    from locking import lock as lock_module

    queue_storage._ClientState.client = None
    lock_module._ClientState.client = None
    lock_module._ClientState.url = None

    async with httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


def _make_token(user_id: _uuid.UUID) -> str:
    from com.qode.qrew.v1.sales.core.principals import ACCESS, sign

    now = int(time.time())
    return sign(ACCESS, {"sub": str(user_id), "type": "access", "iat": now, "exp": now + 3600})


@pytest.fixture
def auth_headers() -> tuple[_uuid.UUID, dict[str, str]]:
    user_id = _uuid.uuid4()
    return user_id, {"Authorization": f"Bearer {_make_token(user_id)}"}


@pytest_asyncio.fixture
async def seed_event(
    test_session_factory: async_sessionmaker[AsyncSession],
) -> tuple[_uuid.UUID, _uuid.UUID]:
    from sqlalchemy import text

    event_id = _uuid.uuid4()
    ticket_type_id = _uuid.uuid4()
    now = datetime.now(UTC)
    async with test_session_factory() as session, session.begin():
        await session.execute(
            text("""
                INSERT INTO sales.event_context
                (event_id, status, sale_starts_at, sale_ends_at, max_tickets_per_user,
                 queue_required, queue_admit_rate_per_minute)
                VALUES (:event_id, 'published', :sale_starts, :sale_ends, 10, false, 50)
            """),
            {
                "event_id": event_id,
                "sale_starts": now - timedelta(hours=1),
                "sale_ends": now + timedelta(hours=1),
            },
        )
        await session.execute(
            text("""
                INSERT INTO sales.ticket_type_inventory
                (ticket_type_id, event_id, capacity, reserved_count, price_cents, currency)
                VALUES (:ticket_type_id, :event_id, 100, 0, 1500, 'EUR')
            """),
            {"ticket_type_id": ticket_type_id, "event_id": event_id},
        )
    return event_id, ticket_type_id


@pytest_asyncio.fixture
async def seed_queue_event(
    test_session_factory: async_sessionmaker[AsyncSession],
) -> tuple[_uuid.UUID, _uuid.UUID]:
    from sqlalchemy import text

    event_id = _uuid.uuid4()
    ticket_type_id = _uuid.uuid4()
    now = datetime.now(UTC)
    async with test_session_factory() as session, session.begin():
        await session.execute(
            text("""
                INSERT INTO sales.event_context
                (event_id, status, sale_starts_at, sale_ends_at, max_tickets_per_user,
                 queue_required, queue_admit_rate_per_minute)
                VALUES (:event_id, 'published', :sale_starts, :sale_ends, 10, true, 50)
            """),
            {
                "event_id": event_id,
                "sale_starts": now - timedelta(hours=1),
                "sale_ends": now + timedelta(hours=1),
            },
        )
        await session.execute(
            text("""
                INSERT INTO sales.ticket_type_inventory
                (ticket_type_id, event_id, capacity, reserved_count, price_cents, currency)
                VALUES (:ticket_type_id, :event_id, 100, 0, 1500, 'EUR')
            """),
            {"ticket_type_id": ticket_type_id, "event_id": event_id},
        )
    return event_id, ticket_type_id
