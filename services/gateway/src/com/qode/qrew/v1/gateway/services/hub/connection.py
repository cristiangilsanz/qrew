import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

import structlog
from fastapi import WebSocket
from starlette.websockets import WebSocketState

from com.qode.qrew.v1.gateway.services.hub.close_codes import WS_CLOSE_INTERNAL, WS_CLOSE_NORMAL

logger = structlog.get_logger(__name__)


@dataclass(eq=False)
class Connection:
    """One authenticated WebSocket connection."""

    socket: WebSocket
    claims: dict[str, object]
    queue_size: int = 64
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    _queue: asyncio.Queue[dict[str, Any]] = field(init=False)
    _closed: bool = field(default=False, init=False)
    _last_pong: float = field(default=0.0, init=False)

    def __post_init__(self) -> None:
        self._queue = asyncio.Queue(maxsize=self.queue_size)
        self._last_pong = time.monotonic()

    @property
    def closed(self) -> bool:
        return self._closed or self.socket.application_state != WebSocketState.CONNECTED

    async def enqueue(self, message: dict[str, Any]) -> bool:
        if self.closed:
            return False
        try:
            self._queue.put_nowait(message)
            return True
        except asyncio.QueueFull:
            return False

    async def writer(self) -> None:
        try:
            while not self.closed:
                message = await self._queue.get()
                await self.socket.send_json(message)
        except Exception as exc:
            await logger.awarning("ws_writer_error", error=repr(exc))
            await self.close(WS_CLOSE_INTERNAL)

    async def close(self, code: int = WS_CLOSE_NORMAL, reason: str = "") -> None:
        if self._closed:
            return
        self._closed = True
        try:
            if self.socket.application_state == WebSocketState.CONNECTED:
                await self.socket.close(code=code, reason=reason)
        except Exception:
            pass

    def record_pong(self, now: float) -> None:
        self._last_pong = now

    def is_stale(self, now: float, max_silence_seconds: float) -> bool:
        return now - self._last_pong > max_silence_seconds
