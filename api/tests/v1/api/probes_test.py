from collections.abc import AsyncGenerator, Iterator
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient
from sqlalchemy.exc import OperationalError

from com.qode.qrew.v1.service.core.infra.database import get_db
from com.qode.qrew.v1.service.core.infra.redis import get_redis
from com.qode.qrew.v1.service.main import app


async def test_healthz_returns_ok(client: AsyncClient) -> None:
    response = await client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.fixture
def healthy_overrides() -> Iterator[None]:
    async def _db() -> AsyncGenerator[MagicMock, None]:
        session = MagicMock()
        session.execute = AsyncMock(return_value=None)
        yield session

    async def _redis() -> AsyncGenerator[MagicMock, None]:
        client = MagicMock()
        client.ping = AsyncMock(return_value=True)
        yield client

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_redis] = _redis
    yield
    app.dependency_overrides.clear()


async def test_readyz_returns_200_when_deps_healthy(
    client: AsyncClient, healthy_overrides: None
) -> None:
    del healthy_overrides
    response = await client.get("/readyz")
    assert response.status_code == 200
    body = response.json()
    assert body["failures"] == []
    assert body["deps"]["db"] == "ok"
    assert body["deps"]["redis"] == "ok"


@pytest.fixture
def db_broken_overrides() -> Iterator[None]:
    async def _db() -> AsyncGenerator[MagicMock, None]:
        session = MagicMock()
        session.execute = AsyncMock(
            side_effect=OperationalError("statement", {}, Exception("down"))
        )
        yield session

    async def _redis() -> AsyncGenerator[MagicMock, None]:
        client = MagicMock()
        client.ping = AsyncMock(return_value=True)
        yield client

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_redis] = _redis
    yield
    app.dependency_overrides.clear()


async def test_readyz_returns_503_when_db_unreachable(
    client: AsyncClient, db_broken_overrides: None
) -> None:
    del db_broken_overrides
    response = await client.get("/readyz")
    assert response.status_code == 503
    body = response.json()
    assert "db" in body["failures"]
    assert body["deps"]["db"] == "fail"
