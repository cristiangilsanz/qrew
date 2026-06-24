import os
import pathlib
import time
import uuid as _uuid
from collections.abc import AsyncGenerator

import fakeredis
import fakeredis.aioredis
import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from unittest.mock import patch

os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("IDEMPOTENCY_ENABLED", "false")
os.environ.setdefault("RATELIMIT_ENABLED", "false")
os.environ.setdefault("NATS_URL", "")
os.environ.setdefault("OTEL_ENABLED", "false")


def _get_test_db_url() -> str | None:
    explicit = os.environ.get("TICKETING_TEST_DB_URL") or os.environ.get("DATABASE_URL")
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
            "Set TICKETING_TEST_DB_URL or start Docker (testcontainers)."
        )
    return url


@pytest.fixture(scope="session", autouse=True)
def setup_test_infrastructure(test_db_url: str) -> None:
    from com.qode.qrew.v1.ticketing.core.config import settings
    import com.qode.qrew.v1.ticketing.core.database as db_module

    settings.database_url = test_db_url
    settings.debug = True
    settings.idempotency_enabled = False
    settings.nats_url = ""
    settings.internal_api_key = "test-internal-key"
    settings.ratelimit_enabled = False
    settings.ticket_qr_reassert_window_seconds = 300
    settings.ticket_qr_attestation_max_age_hours = 24

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
    import com.qode.qrew.v1.ticketing.core.database as db_module

    return db_module.AsyncSessionLocal


@pytest_asyncio.fixture
async def client(
    setup_test_infrastructure: None,
    patch_redis_globally: None,
) -> AsyncGenerator[httpx.AsyncClient, None]:
    from com.qode.qrew.v1.ticketing.app import app
    from locking import lock as lock_module

    lock_module._ClientState.client = None
    lock_module._ClientState.url = None

    async with httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


def _make_token(
    user_id: _uuid.UUID,
    device_id: _uuid.UUID | None = None,
    last_asserted_at: float | None = None,
) -> str:
    from com.qode.qrew.v1.ticketing.core.principals import ACCESS, sign

    now = int(time.time())
    claims: dict = {"sub": str(user_id), "type": "access", "iat": now, "exp": now + 3600}
    if device_id is not None:
        claims["device_id"] = str(device_id)
    claims["last_asserted_at"] = last_asserted_at if last_asserted_at is not None else float(now)
    return sign(ACCESS, claims)


@pytest.fixture
def make_auth_headers():
    def _factory(
        user_id: _uuid.UUID,
        device_id: _uuid.UUID | None = None,
        last_asserted_at: float | None = None,
    ) -> dict[str, str]:
        return {"Authorization": f"Bearer {_make_token(user_id, device_id, last_asserted_at)}"}

    return _factory
