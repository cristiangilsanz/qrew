from collections.abc import Iterator
from typing import Any

import fakeredis.aioredis
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from com.qode.qrew.v1.service.core.api import (
    default_responses,
    register_exception_handlers,
)
from com.qode.qrew.v1.service.core.idempotency import (
    HEADER_NAME,
    IdempotencyMiddleware,
    IdempotencyStore,
    idempotent,
)
from com.qode.qrew.v1.service.core.idempotency import middleware as middleware_module
from com.qode.qrew.v1.service.settings import settings


@pytest.fixture
def fake_redis() -> Any:
    return fakeredis.aioredis.FakeRedis()


@pytest.fixture(autouse=True)
def _enable_idempotency(fake_redis: Any) -> Iterator[None]:  # pyright: ignore[reportUnusedFunction]
    previous_enabled = settings.idempotency_enabled
    settings.idempotency_enabled = True
    middleware_module._StoreState.redis = fake_redis  # pyright: ignore[reportPrivateUsage]
    middleware_module._StoreState.store = IdempotencyStore(  # pyright: ignore[reportPrivateUsage]
        fake_redis, lock_seconds=settings.idempotency_lock_seconds
    )
    yield
    middleware_module._StoreState.redis = None  # pyright: ignore[reportPrivateUsage]
    middleware_module._StoreState.store = None  # pyright: ignore[reportPrivateUsage]
    settings.idempotency_enabled = previous_enabled


def _build_app() -> FastAPI:
    app = FastAPI(responses=default_responses)
    register_exception_handlers(app)
    app.add_middleware(IdempotencyMiddleware)

    call_count = {"n": 0}

    @idempotent(scope="global", ttl_seconds=300)
    async def create_thing(payload: dict[str, str]) -> dict[str, Any]:
        call_count["n"] += 1
        return {"echo": payload["name"], "calls": call_count["n"]}

    async def unmarked(payload: dict[str, str]) -> dict[str, str]:
        return {"echo": payload["name"]}

    @idempotent(scope="global", required=True)
    async def strict(payload: dict[str, str]) -> dict[str, str]:
        return {"echo": payload["name"]}

    app.add_api_route("/things", create_thing, methods=["POST"])
    app.add_api_route("/unmarked", unmarked, methods=["POST"])
    app.add_api_route("/strict", strict, methods=["POST"])
    app.state.call_count = call_count
    return app


def test_first_call_runs_handler() -> None:
    app = _build_app()
    with TestClient(app) as client:
        r = client.post("/things", json={"name": "a"}, headers={HEADER_NAME: "k1"})
    assert r.status_code == 200
    assert r.json()["calls"] == 1


def test_replay_returns_cached_without_re_running_handler() -> None:
    app = _build_app()
    with TestClient(app) as client:
        first = client.post("/things", json={"name": "a"}, headers={HEADER_NAME: "k1"})
        second = client.post("/things", json={"name": "a"}, headers={HEADER_NAME: "k1"})
    assert first.json() == second.json()
    assert app.state.call_count["n"] == 1
    assert second.headers.get("idempotency-replayed") == "true"


def test_same_key_different_body_is_rejected() -> None:
    app = _build_app()
    with TestClient(app) as client:
        client.post("/things", json={"name": "a"}, headers={HEADER_NAME: "k1"})
        conflict = client.post(
            "/things", json={"name": "b"}, headers={HEADER_NAME: "k1"}
        )
    assert conflict.status_code == 422
    assert "already used" in conflict.json()["detail"]["message"].lower()


def test_unmarked_route_ignores_header() -> None:
    app = _build_app()
    with TestClient(app) as client:
        r = client.post("/unmarked", json={"name": "x"}, headers={HEADER_NAME: "k"})
    assert r.status_code == 200


def test_required_header_missing_returns_400() -> None:
    app = _build_app()
    with TestClient(app) as client:
        r = client.post("/strict", json={"name": "x"})
    assert r.status_code == 400
    assert "required" in r.json()["detail"]["message"].lower()


def test_disabled_globally_passes_through() -> None:
    settings.idempotency_enabled = False
    app = _build_app()
    with TestClient(app) as client:
        first = client.post("/things", json={"name": "a"}, headers={HEADER_NAME: "k1"})
        second = client.post("/things", json={"name": "a"}, headers={HEADER_NAME: "k1"})
    assert first.status_code == 200
    assert second.status_code == 200
    assert app.state.call_count["n"] == 2
