from typing import Any

import fakeredis.aioredis
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from com.qode.qrew.v1.service.core.api import (
    default_responses,
    register_exception_handlers,
)
from com.qode.qrew.v1.service.core.ratelimit import (
    RateLimiter,
    rate_limit,
)


@pytest.fixture
def redis_client() -> Any:
    return fakeredis.aioredis.FakeRedis()


def _build_app(limiter: RateLimiter) -> FastAPI:
    app = FastAPI(responses=default_responses)
    register_exception_handlers(app)

    async def factory(_request: Request) -> RateLimiter:
        return limiter

    @rate_limit([("ip", 2, 60)], limiter_factory=factory)
    async def hello(request: Request) -> dict[str, str]:
        del request
        return {"hello": "world"}

    app.add_api_route("/hello", hello, methods=["GET"])
    return app


def test_decorator_allows_under_limit(redis_client: Any) -> None:
    app = _build_app(RateLimiter(redis_client))
    with TestClient(app) as client:
        assert client.get("/hello").status_code == 200
        assert client.get("/hello").status_code == 200


def test_decorator_blocks_over_limit_with_canonical_body(redis_client: Any) -> None:
    app = _build_app(RateLimiter(redis_client))
    with TestClient(app) as client:
        client.get("/hello")
        client.get("/hello")
        response = client.get("/hello")
    assert response.status_code == 429
    assert response.headers["Retry-After"]
    body = response.json()
    assert body["detail"]["message"] == "Rate limit exceeded"


def test_decorator_rejects_unknown_scope_at_definition() -> None:
    with pytest.raises(ValueError, match="unknown rate-limit scope"):
        rate_limit([("alien", 5, 60)])
