import os
import uuid as _uuid

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
        host = _r.get_container_host_ip()
        port = _r.get_exposed_port(6379)
        return f"redis://{host}:{port}/0"
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
    suffix = str(int(_uuid.uuid4().int % 90_000_000) + 10_000_000)
    return f"+346{suffix}"


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


async def _verify_email(client: httpx.AsyncClient, db: AsyncSession, email: str) -> None:
    token = await _issued_token(db, email, "email_account_verify", "token")
    resp = await client.post("/v1/auth/registration/verify-email", json={"token": token})
    assert resp.status_code == 200, resp.text


async def _issued_token(db: AsyncSession, destination: str, template_key: str, field: str) -> str:
    """Read a single-use secret from the notification issued to that destination.

    The destination column is encrypted with a non-deterministic scheme, so the
    match happens after decryption instead of in the query.
    """
    from sqlalchemy import select
    from com.qode.qrew.v1.identity.models.notification import Notification

    result = await db.execute(
        select(Notification)
        .where(Notification.template_key == template_key)
        .order_by(Notification.created_at.desc())
        .limit(50)
    )
    for notification in result.scalars():
        if notification.destination == destination:
            return str(notification.payload[field])
    raise AssertionError(f"no {template_key} notification issued to {destination}")


async def _complete_setup(db: AsyncSession, user_id: _uuid.UUID) -> None:
    """Bring the account to the state that login requires for a full session.

    Onboarding demands a verified phone, a submitted document and a registered
    passkey, and the last one cannot be produced without a WebAuthn ceremony, so
    the state is written straight into the database.
    """
    import os as _os

    from sqlalchemy import update
    from com.qode.qrew.v1.identity.models.passkey import PasskeyCredential
    from com.qode.qrew.v1.identity.models.user import KycStatus, User

    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(phone_number_verified=True, kyc_status=KycStatus.approved)
    )
    db.add(
        PasskeyCredential(
            user_id=user_id,
            credential_id=_os.urandom(32),
            public_key=_os.urandom(64),
            aaguid=str(_uuid.uuid4()),
            name="test-passkey",
        )
    )
    await db.commit()


@pytest_asyncio.fixture
async def registered_user(client: httpx.AsyncClient, db_session: AsyncSession) -> dict:
    """Register, verify email and finish onboarding. Returns the account data."""
    email = _unique_email()
    phone = _unique_phone()
    data = await _register(client, email, phone)
    await _verify_email(client, db_session, email)
    await _complete_setup(db_session, _uuid.UUID(data["id"]))
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
    await _complete_setup(db_session, user_id)

    resp = await client.post(
        "/v1/auth/login",
        json={"email": email, "password": _DEFAULT_PASSWORD},
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}
