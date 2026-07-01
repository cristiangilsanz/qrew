import os
import uuid as _uuid

from cryptography.fernet import Fernet

# Must be set before any identity app imports so settings + JWT keys pick them up.
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("CAPTCHA_ENABLED", "false")
os.environ.setdefault("HIBP_ENABLED", "false")
os.environ.setdefault("SMTP_ENABLED", "false")
os.environ.setdefault("TWILIO_ENABLED", "false")
os.environ.setdefault("NATS_URL", "")
os.environ.setdefault("IDEMPOTENCY_ENABLED", "false")
os.environ.setdefault("ATTESTATION_ENABLED", "false")
os.environ.setdefault("NOTIFICATION_ENABLED", "false")
os.environ.setdefault("OTEL_ENABLED", "false")
os.environ.setdefault("KYC_AUTO_APPROVE", "false")
os.environ.setdefault("INTERNAL_API_KEY", "test-internal-key")
# Fernet-format keys required by PII crypto and national-ID encryption.
_FERNET_KEY = Fernet.generate_key().decode()
os.environ.setdefault("PII_ENCRYPTION_KEY", _FERNET_KEY)
os.environ.setdefault("NATIONAL_ID_ENCRYPTION_KEY", _FERNET_KEY)
# Storage signing key — arbitrary secret used for HMAC URL signing.
os.environ.setdefault("STORAGE_SIGNING_KEY", _uuid.uuid4().hex * 2)
# JWT: empty → ephemeral EC keys auto-generated when debug=True (see jwt.py).

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
import httpx  # noqa: E402
from httpx import ASGITransport  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402


# ---------------------------------------------------------------------------
# Infrastructure helpers
# ---------------------------------------------------------------------------


def _get_test_db_url() -> str | None:
    """Return the test Postgres URL from env var or by starting a container."""
    explicit = os.environ.get("IDENTITY_TEST_DB_URL") or os.environ.get("DATABASE_URL")
    if explicit:
        # Ensure asyncpg driver.
        for old, new in (
            ("postgresql+psycopg2://", "postgresql+asyncpg://"),
            ("postgresql://", "postgresql+asyncpg://"),
        ):
            if explicit.startswith(old):
                return explicit.replace(old, new, 1)
        return explicit

    # Try testcontainers (requires Docker).
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


def _get_test_redis_url() -> str | None:
    """Return the test Redis URL from env var or by starting a container."""
    explicit = os.environ.get("IDENTITY_TEST_REDIS_URL") or os.environ.get("REDIS_URL")
    if explicit:
        return explicit

    try:
        from testcontainers.redis import RedisContainer  # noqa: PLC0415

        _r = RedisContainer("redis:7-alpine")
        _r.start()
        return _r.get_connection_url()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Session-scoped infrastructure
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def test_db_url() -> str:
    url = _get_test_db_url()
    if url is None:
        pytest.skip(
            "Integration tests require Postgres. "
            "Set IDENTITY_TEST_DB_URL or start Docker (testcontainers)."
        )
    return url


@pytest.fixture(scope="session")
def test_redis_url() -> str:
    url = _get_test_redis_url()
    if url is None:
        pytest.skip(
            "Integration tests require Redis. "
            "Set IDENTITY_TEST_REDIS_URL or start Docker (testcontainers)."
        )
    return url


@pytest.fixture(scope="session", autouse=True)
def setup_test_infrastructure(test_db_url: str, test_redis_url: str) -> None:
    """Patch settings + engine and run Alembic migrations once per session."""
    from com.qode.qrew.v1.identity.core.config import settings
    import com.qode.qrew.v1.identity.core.database as db_module

    settings.database_url = test_db_url
    settings.redis_url = test_redis_url

    new_engine = create_async_engine(test_db_url, pool_pre_ping=True)
    db_module.engine = new_engine
    db_module.AsyncSessionLocal = async_sessionmaker(new_engine, expire_on_commit=False)

    import pathlib
    from alembic.config import Config
    from alembic import command as alembic_command

    alembic_ini = str(pathlib.Path(__file__).parents[3] / "alembic.ini")
    cfg = Config(alembic_ini)
    cfg.set_main_option("sqlalchemy.url", test_db_url)
    alembic_command.upgrade(cfg, "head")


# ---------------------------------------------------------------------------
# Per-test fixtures: session, client, helpers
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def db_session(setup_test_infrastructure: None) -> AsyncSession:
    """Provide a live DB session for direct-DB reads inside fixtures."""
    import com.qode.qrew.v1.identity.core.database as db_module

    async with db_module.AsyncSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client(setup_test_infrastructure: None) -> httpx.AsyncClient:
    """ASGI test client wired to the real FastAPI app."""
    from com.qode.qrew.v1.identity.app import app

    async with httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


def _unique_email() -> str:
    return f"user-{_uuid.uuid4().hex[:10]}@example.com"


def _unique_phone() -> str:
    suffix = str(int(_uuid.uuid4().int % 9_000_000) + 1_000_000)
    return f"+316{suffix}"


_DEFAULT_PASSWORD = "StrongP@ss1!"


async def _register(client: httpx.AsyncClient, email: str, phone: str) -> dict:
    resp = await client.post(
        "/v1/auth/registration/",
        json={
            "full_name": "Test User",
            "email": email,
            "phone_number": phone,
            "password": _DEFAULT_PASSWORD,
            "terms_accepted": True,
            "captcha_token": "test-token",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _verify_email(client: httpx.AsyncClient, db: AsyncSession, user_id: str) -> None:
    from sqlalchemy import select
    from com.qode.qrew.v1.identity.models.user import User

    result = await db.execute(select(User).where(User.id == _uuid.UUID(user_id)))
    user = result.scalar_one()
    token = user.email_verification_token
    resp = await client.post("/v1/auth/registration/verify-email", json={"token": token})
    assert resp.status_code == 200, resp.text


@pytest_asyncio.fixture
async def registered_user(client: httpx.AsyncClient, db_session: AsyncSession) -> dict:
    """Register + verify email. Returns {email, phone, password, user_id}."""
    email = _unique_email()
    phone = _unique_phone()
    data = await _register(client, email, phone)
    await _verify_email(client, db_session, data["id"])
    return {"email": email, "phone": phone, "password": _DEFAULT_PASSWORD, "user_id": data["id"]}


@pytest_asyncio.fixture
async def auth_headers(client: httpx.AsyncClient, registered_user: dict) -> dict:
    """Log in and return Authorization headers for a regular user."""
    resp = await client.post(
        "/v1/auth/login",
        json={"email": registered_user["email"], "password": registered_user["password"]},
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest_asyncio.fixture
async def admin_headers(client: httpx.AsyncClient, db_session: AsyncSession) -> dict:
    """Create an admin user and return Authorization headers."""
    from sqlalchemy import update
    from com.qode.qrew.v1.identity.models.user import User

    email = _unique_email()
    phone = _unique_phone()
    data = await _register(client, email, phone)
    user_id = _uuid.UUID(data["id"])

    await db_session.execute(
        update(User).where(User.id == user_id).values(is_admin=True, email_verified=True)
    )
    await db_session.commit()

    resp = await client.post(
        "/v1/auth/login",
        json={"email": email, "password": _DEFAULT_PASSWORD},
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}
