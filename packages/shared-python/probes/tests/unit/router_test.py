# tests router
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from probes.router import create_probe_router


# handles build client
def _build_client(
    *, db_raises: Exception | None = None, redis_raises: Exception | None = None
) -> TestClient:
    mock_session = AsyncMock()
    if db_raises:
        mock_session.execute = AsyncMock(side_effect=db_raises)
    else:
        mock_session.execute = AsyncMock()

    mock_redis = AsyncMock()
    if redis_raises:
        mock_redis.ping = AsyncMock(side_effect=redis_raises)
    else:
        mock_redis.ping = AsyncMock()

    # handles get db
    async def get_db() -> AsyncGenerator:
        yield mock_session

    # handles get redis
    async def get_redis() -> AsyncGenerator:
        yield mock_redis

    router = create_probe_router(get_db, get_redis)
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


class TestHealthz:
    # verifies that returns 200 ok
    def test_returns_200_ok(self) -> None:
        client = _build_client()
        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestReadyz:
    # verifies that both ok returns 200
    def test_both_ok_returns_200(self) -> None:
        client = _build_client()
        response = client.get("/readyz")
        assert response.status_code == 200
        body = response.json()
        assert body["deps"] == {"db": "ok", "redis": "ok"}
        assert body["failures"] == []

    # verifies that db failure returns 503
    def test_db_failure_returns_503(self) -> None:
        client = _build_client(db_raises=Exception("db error"))
        response = client.get("/readyz")
        assert response.status_code == 503
        body = response.json()
        assert body["deps"]["db"] == "fail"
        assert "db" in body["failures"]

    # verifies that redis failure returns 503
    def test_redis_failure_returns_503(self) -> None:
        client = _build_client(redis_raises=Exception("redis error"))
        response = client.get("/readyz")
        assert response.status_code == 503
        body = response.json()
        assert body["deps"]["redis"] == "fail"
        assert "redis" in body["failures"]

    # verifies that both fail returns 503 with both failures
    def test_both_fail_returns_503_with_both_failures(self) -> None:
        client = _build_client(
            db_raises=Exception("db error"),
            redis_raises=Exception("redis error"),
        )
        response = client.get("/readyz")
        assert response.status_code == 503
        body = response.json()
        assert body["deps"]["db"] == "fail"
        assert body["deps"]["redis"] == "fail"
        assert "db" in body["failures"]
        assert "redis" in body["failures"]
