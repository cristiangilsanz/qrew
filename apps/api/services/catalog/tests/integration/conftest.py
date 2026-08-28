# provides shared pytest fixtures
import os
import time
import uuid as _uuid

os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("IDEMPOTENCY_ENABLED", "false")
os.environ.setdefault("RATELIMIT_ENABLED", "false")
os.environ.setdefault("NATS_URL", "")
os.environ.setdefault("OTEL_ENABLED", "false")

import jwt  # noqa: E402
import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
import httpx  # noqa: E402
from httpx import ASGITransport  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402


# handles get test db url
def _get_test_db_url() -> str | None:
    explicit = os.environ.get("CATALOG_TEST_DB_URL") or os.environ.get("DATABASE_URL")
    if explicit:
        for old, new in (
            ("postgresql+psycopg2://", "postgresql+asyncpg://"),
            ("postgresql://", "postgresql+asyncpg://"),
        ):
            if explicit.startswith(old):
                return explicit.replace(old, new, 1)
        return explicit

    try:
        from testcontainers.postgres import PostgresContainer  # noqa: PLC0415

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


# handles get test redis url
def _get_test_redis_url() -> str | None:
    explicit = os.environ.get("CATALOG_TEST_REDIS_URL") or os.environ.get("REDIS_URL")
    if explicit:
        return explicit

    try:
        from testcontainers.redis import RedisContainer  # noqa: PLC0415

        _r = RedisContainer("redis:7-alpine")
        _r.start()
        host = _r.get_container_host_ip()
        port = _r.get_exposed_port(6379)
        return f"redis://{host}:{port}/0"
    except Exception:
        return None


# verifies that db url
@pytest.fixture(scope="session")
def test_db_url() -> str:
    url = _get_test_db_url()
    if url is None:
        pytest.skip(
            "Integration tests require Postgres. "
            "Set CATALOG_TEST_DB_URL or start Docker (testcontainers)."
        )
    return url


# verifies that redis url
@pytest.fixture(scope="session")
def test_redis_url() -> str:
    url = _get_test_redis_url()
    if url is None:
        pytest.skip(
            "Integration tests require Redis. "
            "Set CATALOG_TEST_REDIS_URL or start Docker (testcontainers)."
        )
    return url


# patch settings + engine and run Alembic migrations once per session
@pytest.fixture(scope="session", autouse=True)
def setup_test_infrastructure(test_db_url: str, test_redis_url: str) -> None:
    from com.qode.qrew.v1.catalog.core.config import settings
    import com.qode.qrew.v1.catalog.core.database as db_module

    settings.database_url = test_db_url
    settings.redis_url = test_redis_url

    new_engine = create_async_engine(test_db_url, pool_pre_ping=True)
    db_module.engine = new_engine
    db_module.AsyncSessionLocal = async_sessionmaker(new_engine, expire_on_commit=False)

    import sys

    for module in list(sys.modules.values()):
        name = getattr(module, "__name__", "")
        if name.startswith("com.qode.qrew") and hasattr(module, "AsyncSessionLocal"):
            module.AsyncSessionLocal = db_module.AsyncSessionLocal

    import pathlib
    from alembic.config import Config
    from alembic import command as alembic_command

    service_root = pathlib.Path(__file__).parents[2]
    cfg = Config(str(service_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(service_root / "migrations"))
    cfg.set_main_option("sqlalchemy.url", test_db_url)
    alembic_command.upgrade(cfg, "head")


# provides db session
@pytest_asyncio.fixture
async def db_session(setup_test_infrastructure: None) -> AsyncSession:
    import com.qode.qrew.v1.catalog.core.database as db_module

    async with db_module.AsyncSessionLocal() as session:
        yield session


# provides client
@pytest_asyncio.fixture
async def client(setup_test_infrastructure: None) -> httpx.AsyncClient:
    from com.qode.qrew.v1.catalog.app import app

    async with httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


# sign a catalog access JWT using the session scoped ephemeral keypair
def _make_token(user_id: _uuid.UUID, *, is_admin: bool = False) -> str:
    from com.qode.qrew.v1.catalog.core.principals import _KEYS, ACCESS, ALGORITHM

    keys = _KEYS[ACCESS]
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": now,
        "exp": now + 3600,
        "adm": is_admin,
    }
    return jwt.encode(payload, keys.private_pem, algorithm=ALGORITHM, headers={"kid": keys.kid})


# handles auth headers for
def auth_headers_for(user_id: _uuid.UUID, *, is_admin: bool = False) -> dict:
    return {"Authorization": f"Bearer {_make_token(user_id, is_admin=is_admin)}"}


# provides user id
@pytest.fixture
def user_id() -> _uuid.UUID:
    return _uuid.uuid4()


# provides auth headers
@pytest.fixture
def auth_headers(user_id: _uuid.UUID) -> dict:
    return auth_headers_for(user_id, is_admin=True)


# provides member headers
@pytest.fixture
def member_headers(user_id: _uuid.UUID) -> dict:
    return auth_headers_for(user_id)
