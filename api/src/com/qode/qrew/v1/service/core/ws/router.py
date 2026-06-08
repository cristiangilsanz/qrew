import asyncio
import time
from typing import Any

import redis.asyncio as aioredis
import structlog
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.service.core.infra.database import get_db
from com.qode.qrew.v1.service.core.infra.redis import get_redis
from com.qode.qrew.v1.service.core.ws.auth import (
    WebSocketAuthError,
    authenticate,
)
from com.qode.qrew.v1.service.core.ws.close_codes import (
    WS_CLOSE_FORBIDDEN,
    WS_CLOSE_INTERNAL,
    WS_CLOSE_NORMAL,
    WS_CLOSE_UNAUTHORIZED,
)
from com.qode.qrew.v1.service.core.ws.connection import Connection
from com.qode.qrew.v1.service.core.ws.hub import Hub
from com.qode.qrew.v1.service.core.ws.registry import resolve
from com.qode.qrew.v1.service.settings import settings

logger = structlog.get_logger(__name__)

router = APIRouter()

_PING = {"type": "ping"}


class _HubState:
    hub: Hub | None = None
    redis: aioredis.Redis | None = None  # type: ignore[type-arg]


async def start_hub() -> None:
    """Open the pub/sub connection and start the dispatcher task."""
    if _HubState.hub is not None:
        return
    _HubState.redis = aioredis.from_url(  # type: ignore[type-arg]
        settings.redis_url, decode_responses=False
    )
    _HubState.hub = Hub(_HubState.redis)
    await _HubState.hub.start()


async def stop_hub() -> None:
    """Close all connections and release the pub/sub Redis client."""
    if _HubState.hub is not None:
        await _HubState.hub.stop()
    if _HubState.redis is not None:
        await _HubState.redis.aclose()
    _HubState.hub = None
    _HubState.redis = None


def get_hub() -> Hub:
    if _HubState.hub is None:
        raise RuntimeError("WebSocket hub is not running")
    return _HubState.hub


async def publish(channel_key: str, payload: dict[str, Any]) -> None:
    """Best-effort publish to a channel; logs and continues on failure."""
    if not settings.ws_enabled or _HubState.hub is None:
        return
    try:
        await _HubState.hub.publish(channel_key, payload)
    except Exception as exc:
        await logger.awarning("ws_publish_failed", error=repr(exc))


@router.websocket("/ws/{channel_key}")
async def channel_socket(
    websocket: WebSocket,
    channel_key: str,
    db: AsyncSession = Depends(get_db),
    redis_client: aioredis.Redis = Depends(get_redis),  # type: ignore[type-arg]
) -> None:
    """Authenticated WebSocket endpoint dispatching to a registered channel."""
    resolution = resolve(channel_key)
    if resolution is None:
        await websocket.close(code=WS_CLOSE_NORMAL, reason="unknown channel")
        return
    definition, params = resolution

    try:
        identity = await authenticate(websocket, db, redis_client)
    except WebSocketAuthError as exc:
        await websocket.close(code=WS_CLOSE_UNAUTHORIZED, reason=str(exc))
        return

    try:
        allowed = await definition.can_subscribe(
            identity.user, params, identity.session
        )
    except Exception as exc:
        await logger.awarning("ws_acl_error", error=repr(exc), channel=channel_key)
        allowed = False
    if not allowed:
        await websocket.close(code=WS_CLOSE_FORBIDDEN, reason="forbidden")
        return

    await websocket.accept(subprotocol=identity.accepted_subprotocol)
    connection = Connection(
        socket=websocket,
        user=identity.user,
        session=identity.session,
        queue_size=definition.queue_size,
    )

    hub = get_hub()
    await hub.subscribe(channel_key, connection)
    writer_task = asyncio.create_task(connection.writer())
    heartbeat_task = asyncio.create_task(_heartbeat(connection))

    try:
        await _read_loop(connection)
    finally:
        writer_task.cancel()
        heartbeat_task.cancel()
        await hub.unsubscribe(channel_key, connection)
        await connection.close(WS_CLOSE_NORMAL)


async def _read_loop(connection: Connection) -> None:
    while not connection.closed:
        try:
            message = await connection.socket.receive_json()
        except WebSocketDisconnect:
            return
        except Exception as exc:
            await logger.awarning("ws_read_error", error=repr(exc))
            await connection.close(WS_CLOSE_INTERNAL)
            return
        if isinstance(message, dict):
            received: dict[str, Any] = message  # type: ignore[assignment]
            if received.get("type") == "pong":
                connection.record_pong(time.monotonic())


async def _heartbeat(connection: Connection) -> None:
    ping_interval = settings.ws_heartbeat_seconds
    try:
        while not connection.closed:
            await asyncio.sleep(ping_interval)
            if connection.closed:
                return
            await connection.enqueue(_PING)
    except asyncio.CancelledError:
        raise
