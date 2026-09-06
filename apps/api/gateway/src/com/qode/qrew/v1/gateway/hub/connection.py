# wraps a websocket with its outbound queue and liveness tracking
import asyncio
import time
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

import structlog
from fastapi import WebSocket
from starlette.websockets import WebSocketState

from com.qode.qrew.v1.gateway.hub.close_codes import WS_CLOSE_INTERNAL, WS_CLOSE_NORMAL

logger = structlog.get_logger(__name__)


@dataclass(eq=False)
class Connection:
    socket: WebSocket
    claims: dict[str, object]
    queue_size: int = 64
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    _queue: asyncio.Queue[Mapping[str, Any]] = field(init=False)
    _closed: bool = field(default=False, init=False)
    _last_pong: float = field(default=0.0, init=False)

    # initializes the outbound queue and the last pong timestamp
    def __post_init__(self) -> None:
        self._queue = asyncio.Queue(maxsize=self.queue_size)
        self._last_pong = time.monotonic()

    # reports whether the connection has been closed
    @property
    def closed(self) -> bool:
        return self._closed or self.socket.application_state != WebSocketState.CONNECTED

    # queues a message for delivery unless the connection is closed or full
    async def enqueue(self, message: Mapping[str, Any]) -> bool:
        if self.closed:
            return False
        try:
            self._queue.put_nowait(message)
            return True
        except asyncio.QueueFull:
            return False

    # sends every queued message until the connection closes
    async def writer(self) -> None:
        try:
            while not self.closed:
                message = await self._queue.get()
                await self.socket.send_json(message)
        except Exception as exc:
            await logger.awarning("ws_writer_error", error=repr(exc))
            await self.close(WS_CLOSE_INTERNAL)

    # closes the underlying websocket once
    async def close(self, code: int = WS_CLOSE_NORMAL, reason: str = "") -> None:
        if self._closed:
            return
        self._closed = True
        try:
            if self.socket.application_state == WebSocketState.CONNECTED:
                await self.socket.close(code=code, reason=reason)
        except Exception as exc:
            await logger.adebug("gateway.connection.close_failed", error=repr(exc))

    # records the time of the connection's last pong
    def record_pong(self, now: float) -> None:
        self._last_pong = now

    # checks whether the connection has been silent past the allowed window
    def is_stale(self, now: float, max_silence_seconds: float) -> bool:
        return now - self._last_pong > max_silence_seconds
