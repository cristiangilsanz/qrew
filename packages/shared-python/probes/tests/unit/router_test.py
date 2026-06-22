from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from probes.router import create_probe_router


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

    async def get_db() -> AsyncGenerator:
        yield mock_session

    async def get_redis() -> AsyncGenerator:
        yield mock_redis

    router = create_probe_router(get_db, get_redis)
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


class TestHealthz:
    def test_returns_200_ok(self) -> None:
        client = _build_client()
        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestReadyz:
    def test_both_ok_returns_200(self) -> None:
        client = _build_client()
        response = client.get("/readyz")
        assert response.status_code == 200
        body = response.json()
        assert body["deps"] == {"db": "ok", "redis": "ok"}
        assert body["failures"] == []

    def test_db_failure_returns_503(self) -> None:
        client = _build_client(db_raises=Exception("db error"))
        response = client.get("/readyz")
        assert response.status_code == 503
        body = response.json()
        assert body["deps"]["db"] == "fail"
        assert "db" in body["failures"]

    def test_redis_failure_returns_503(self) -> None:
        client = _build_client(redis_raises=Exception("redis error"))
        response = client.get("/readyz")
        assert response.status_code == 503
        body = response.json()
        assert body["deps"]["redis"] == "fail"
        assert "redis" in body["failures"]

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
