import pathlib

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

try:
    from testcontainers.postgres import PostgresContainer
    import docker

    docker.from_env(timeout=5)
    _DOCKER_AVAILABLE = True
except Exception:
    _DOCKER_AVAILABLE = False

pytestmark = pytest.mark.integration


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "integration: integration tests requiring Docker")


@pytest.fixture(scope="session")
def postgres_container():
    if not _DOCKER_AVAILABLE:
        pytest.skip("Docker not available")
    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg


@pytest.fixture(scope="session")
def engine(postgres_container):
    url = postgres_container.get_connection_url().replace("psycopg2", "asyncpg")

    from com.qode.qrew.v1.audit.core.config import settings

    settings.debug = True
    settings.internal_api_key = "test-key"
    settings.idempotency_enabled = False
    settings.nats_url = ""
    settings.database_url = url

    from alembic import command as alembic_command
    from alembic.config import Config

    alembic_ini = str(pathlib.Path(__file__).parents[2] / "alembic.ini")
    cfg = Config(alembic_ini)
    cfg.set_main_option("sqlalchemy.url", url)
    alembic_command.upgrade(cfg, "head")

    return create_async_engine(url)


@pytest.fixture(scope="session")
def session_factory(engine):
    import com.qode.qrew.v1.audit.services.verifier as verifier_module

    factory = async_sessionmaker(engine, expire_on_commit=False)
    verifier_module.AsyncSessionLocal = factory
    return factory


@pytest_asyncio.fixture
async def db(session_factory: async_sessionmaker) -> AsyncSession:  # type: ignore[type-arg]
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(session_factory: async_sessionmaker):  # type: ignore[type-arg]
    from com.qode.qrew.v1.audit.app import app

    # session_factory fixture has already patched verifier_module.AsyncSessionLocal,
    # so the app uses the test DB without any further dependency overrides.
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
def internal_headers() -> dict[str, str]:
    return {"X-Internal-Key": "test-key"}
