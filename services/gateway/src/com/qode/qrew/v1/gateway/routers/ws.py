import asyncio
import time
from typing import Any

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from com.qode.qrew.v1.gateway.services.channels.registry import resolve
from com.qode.qrew.v1.gateway.services.auth.auth import WebSocketAuthError, authenticate
from com.qode.qrew.v1.gateway.services.hub.close_codes import (
    WS_CLOSE_FORBIDDEN,
    WS_CLOSE_INTERNAL,
    WS_CLOSE_NORMAL,
    WS_CLOSE_UNAUTHORIZED,
)
from com.qode.qrew.v1.gateway.services.hub.connection import Connection
from com.qode.qrew.v1.gateway.services.hub.hub import get_hub
from com.qode.qrew.v1.gateway.settings import settings

logger = structlog.get_logger(__name__)

router = APIRouter()

_PING: dict[str, Any] = {"type": "ping"}


@router.websocket("/ws/{channel_key:path}")
async def channel_socket(websocket: WebSocket, channel_key: str) -> None:
    resolution = resolve(channel_key)
    if resolution is None:
        await websocket.close(code=WS_CLOSE_NORMAL, reason="unknown channel")
        return
    definition, params = resolution

    try:
        identity = authenticate(websocket)
    except WebSocketAuthError as exc:
        await websocket.close(code=WS_CLOSE_UNAUTHORIZED, reason=str(exc))
        return

    try:
        allowed = await definition.can_subscribe(identity.claims, params)
    except Exception as exc:
        await logger.awarning("ws_acl_error", error=repr(exc), channel=channel_key)
        allowed = False
    if not allowed:
        await websocket.close(code=WS_CLOSE_FORBIDDEN, reason="forbidden")
        return

    await websocket.accept(subprotocol=identity.accepted_subprotocol)
    connection = Connection(
        socket=websocket,
        claims=identity.claims,
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
        if isinstance(message, dict) and message.get("type") == "pong":  # type: ignore[reportUnknownMemberType]
            connection.record_pong(time.monotonic())


async def _heartbeat(connection: Connection) -> None:
    try:
        while not connection.closed:
            await asyncio.sleep(settings.ws_heartbeat_seconds)
            if connection.closed:
                return
            await connection.enqueue(_PING)
    except asyncio.CancelledError:
        raise
