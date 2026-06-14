import json
from collections.abc import Awaitable, Callable
from typing import Any

import redis.asyncio as aioredis
import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Match
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_409_CONFLICT,
    HTTP_422_UNPROCESSABLE_CONTENT,
)

from com.qode.qrew.v1.sales.core.idempotency.decorator import (
    IdempotencyConfig,
    get_config,
)
from com.qode.qrew.v1.sales.core.idempotency.fingerprint import compute_fingerprint
from com.qode.qrew.v1.sales.core.idempotency.store import (
    IdempotencyStore,
    StoredResponse,
    sanitise_response_headers,
)
from com.qode.qrew.v1.sales.settings import settings

logger = structlog.get_logger(__name__)

HEADER_NAME = "Idempotency-Key"


def _error_response(
    status_code: int, message: str, headers: dict[str, str] | None = None
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"detail": {"message": message, "field": HEADER_NAME}},
        headers=headers,
    )


class _StoreState:
    redis: aioredis.Redis | None = None  # type: ignore[type-arg]
    store: IdempotencyStore | None = None


async def _ensure_store() -> IdempotencyStore:
    if _StoreState.store is None:
        _StoreState.redis = aioredis.from_url(  # type: ignore[type-arg]
            settings.redis_url, decode_responses=False
        )
        _StoreState.store = IdempotencyStore(
            _StoreState.redis,
            lock_seconds=settings.idempotency_lock_seconds,
        )
    return _StoreState.store


async def close_idempotency_store() -> None:
    if _StoreState.redis is not None:
        await _StoreState.redis.aclose()
    _StoreState.redis = None
    _StoreState.store = None


def _route_config(request: Request) -> IdempotencyConfig | None:
    router = getattr(request.app, "router", None)
    if router is None:
        return None
    for route in router.routes:
        match, _ = route.matches(request.scope)
        if match != Match.FULL:
            continue
        endpoint = getattr(route, "endpoint", None)
        config = get_config(endpoint)
        if config is not None:
            return config
    return None


def _user_id(request: Request) -> str | None:
    actor = getattr(request.state, "current_user_id", None)
    return str(actor) if actor else None


class IdempotencyMiddleware(BaseHTTPMiddleware):
    async def dispatch(  # noqa: PLR0911
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if not settings.idempotency_enabled:
            return await call_next(request)

        config = _route_config(request)
        if config is None:
            return await call_next(request)

        key = request.headers.get(HEADER_NAME)
        if key is None:
            if config.required:
                return _error_response(
                    HTTP_400_BAD_REQUEST,
                    "Idempotency-Key header is required",
                )
            return await call_next(request)

        body = await request.body()
        fingerprint = compute_fingerprint(
            request.method, request.url.path, request.url.query, body
        )

        try:
            store = await _ensure_store()
            user_id = _user_id(request)
            lock_result = await store.acquire(config.scope, user_id, key)
        except aioredis.RedisError as exc:
            await logger.awarning("idempotency_redis_unavailable", error=repr(exc))
            return await self._replay_body(request, call_next, body)

        if (
            lock_result.cached is not None
            and lock_result.cached.fingerprint == fingerprint
        ):
            await store.release(config.scope, user_id, key)
            return self._materialise(lock_result.cached)

        if (
            lock_result.cached is not None
            and lock_result.cached.fingerprint != fingerprint
        ):
            await store.release(config.scope, user_id, key)
            return _error_response(
                HTTP_422_UNPROCESSABLE_CONTENT,
                "Idempotency-Key already used with a different request",
            )

        if not lock_result.acquired:
            return _error_response(
                HTTP_409_CONFLICT,
                "request is already being processed",
                headers={"Retry-After": "5"},
            )

        try:
            response = await self._replay_body(request, call_next, body)
            captured = await self._capture(response)
            await store.save(
                config.scope,
                user_id,
                key,
                StoredResponse(
                    status_code=response.status_code,
                    headers=sanitise_response_headers(dict(response.headers)),
                    body=captured,
                    fingerprint=fingerprint,
                ),
                ttl_seconds=config.ttl_seconds,
            )
            return self._rebuild_response(response, captured)
        except Exception:
            await store.release(config.scope, user_id, key)
            raise

    async def _replay_body(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
        body: bytes,
    ) -> Response:
        async def receive() -> dict[str, object]:
            return {"type": "http.request", "body": body, "more_body": False}

        request.scope["body"] = body
        downstream = Request(request.scope, receive)
        return await call_next(downstream)

    async def _capture(self, response: Response) -> bytes:
        chunks: list[bytes] = []
        body_iterator: Any = getattr(response, "body_iterator", None)
        if body_iterator is not None:
            async for chunk in body_iterator:
                if isinstance(chunk, bytes):
                    chunks.append(chunk)
                else:
                    chunks.append(str(chunk).encode())
            return b"".join(chunks)
        body = getattr(response, "body", b"")
        if isinstance(body, str):
            return body.encode()
        return body  # type: ignore[no-any-return]

    def _rebuild_response(self, response: Response, body: bytes) -> Response:
        return Response(
            content=body,
            status_code=response.status_code,
            headers={
                k: v
                for k, v in response.headers.items()
                if k.lower() != "content-length"
            },
            media_type=response.media_type,
        )

    def _materialise(self, cached: StoredResponse) -> Response:
        headers = dict(cached.headers)
        headers["Idempotency-Replayed"] = "true"
        body = cached.body
        media_type = headers.get("content-type")
        if media_type is None or media_type.startswith("application/json"):
            try:
                payload = json.loads(body)
                return JSONResponse(
                    status_code=cached.status_code,
                    content=payload,
                    headers=headers,
                )
            except json.JSONDecodeError:
                pass
        return Response(
            content=body,
            status_code=cached.status_code,
            headers=headers,
            media_type=media_type,
        )
