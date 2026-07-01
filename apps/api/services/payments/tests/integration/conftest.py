import os
import pathlib
import time
import uuid as _uuid
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, patch

import fakeredis
import fakeredis.aioredis
import httpx
import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("IDEMPOTENCY_ENABLED", "false")
os.environ.setdefault("RATELIMIT_ENABLED", "false")
os.environ.setdefault("NATS_URL", "")
os.environ.setdefault("PII_ENCRYPTION_KEY", Fernet.generate_key().decode())


def _get_test_db_url() -> str | None:
    explicit = os.environ.get("PAYMENTS_TEST_DB_URL") or os.environ.get("DATABASE_URL")
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
            "Set PAYMENTS_TEST_DB_URL or start Docker (testcontainers)."
        )
    return url


@pytest.fixture(scope="session", autouse=True)
def setup_test_infrastructure(test_db_url: str) -> None:
    import com.qode.qrew.v1.payments.core.database as db_module
    from com.qode.qrew.v1.payments.core.config import settings

    settings.database_url = test_db_url
    settings.debug = True
    settings.idempotency_enabled = False
    settings.nats_url = ""
    settings.internal_api_key = "test-internal-key"
    settings.ratelimit_enabled = False
    settings.pii_encryption_key = os.environ["PII_ENCRYPTION_KEY"]

    new_engine = create_async_engine(test_db_url, pool_pre_ping=True)
    db_module.engine = new_engine
    db_module.AsyncSessionLocal = async_sessionmaker(
        new_engine, class_=AsyncSession, expire_on_commit=False
    )

    alembic_ini = str(pathlib.Path(__file__).parents[2] / "alembic.ini")
    from alembic import command as alembic_command
    from alembic.config import Config

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
    import com.qode.qrew.v1.payments.core.database as db_module

    return db_module.AsyncSessionLocal


@pytest.fixture
def mock_stripe() -> AsyncMock:
    from com.qode.qrew.v1.payments.services.infrastructure.stripe_client import CreatedIntent

    mock = AsyncMock()
    mock.create_payment_intent.return_value = CreatedIntent(
        intent_id="pi_test_123",
        client_secret="pi_test_123_secret_abc",
        status="requires_action",
    )
    mock.verify_webhook.return_value = {
        "id": f"evt_{_uuid.uuid4().hex[:12]}",
        "type": "payment_intent.succeeded",
        "data": {"object": {"id": "pi_test_123"}},
    }
    return mock


@pytest_asyncio.fixture
async def client(
    setup_test_infrastructure: None,
    patch_redis_globally: None,
    mock_stripe: AsyncMock,
) -> AsyncGenerator[httpx.AsyncClient, None]:
    from com.qode.qrew.v1.payments.app import app
    from com.qode.qrew.v1.payments.core.dependencies import get_stripe_client
    from com.qode.qrew.v1.payments.services.infrastructure.webhooks.idempotency import (
        _ClientState,
    )

    _ClientState.client = None
    app.dependency_overrides[get_stripe_client] = lambda: mock_stripe

    async with httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c

    app.dependency_overrides.pop(get_stripe_client, None)


def _make_token(user_id: _uuid.UUID) -> str:
    import jwt as pyjwt

    from com.qode.qrew.v1.payments.core.principals import ACCESS, ALGORITHM, _KEYS

    key = _KEYS[ACCESS]
    now = int(time.time())
    return pyjwt.encode(
        {"sub": str(user_id), "type": "access", "iat": now, "exp": now + 3600},
        key.private_pem,
        algorithm=ALGORITHM,
        headers={"kid": key.kid},
    )


@pytest.fixture
def auth_headers() -> tuple[_uuid.UUID, dict[str, str]]:
    user_id = _uuid.uuid4()
    return user_id, {"Authorization": f"Bearer {_make_token(user_id)}"}
