"""Tracks active WebSocket connections grouped by channel for in-process message delivery."""

import asyncio
import contextlib
import time
from typing import Any

import structlog

from com.qode.qrew.v1.gateway.hub.close_codes import WS_CLOSE_INTERNAL, WS_CLOSE_OVERLOAD
from com.qode.qrew.v1.gateway.hub.connection import Connection
from com.qode.qrew.v1.gateway.core.config import settings

logger = structlog.get_logger(__name__)


class Hub:
    """Maps channel keys to the local set of connected subscribers."""

    def __init__(self) -> None:
        self._local: dict[str, set[Connection]] = {}
        self._lock = asyncio.Lock()
        self._reaper_task: asyncio.Task[None] | None = None
        self._running = False

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._reaper_task = asyncio.create_task(self._reaper())

    async def stop(self) -> None:
        self._running = False
        if self._reaper_task is not None:
            self._reaper_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._reaper_task
            self._reaper_task = None
        connections = {c for conns in self._local.values() for c in conns}
        for connection in connections:
            await connection.close(1001, "shutdown")
        self._local.clear()

    async def subscribe(self, channel_key: str, connection: Connection) -> None:
        async with self._lock:
            self._local.setdefault(channel_key, set()).add(connection)

    async def unsubscribe(self, channel_key: str, connection: Connection) -> None:
        async with self._lock:
            subscribers = self._local.get(channel_key)
            if subscribers is None:
                return
            subscribers.discard(connection)
            if not subscribers:
                self._local.pop(channel_key, None)

    async def deliver(self, channel_key: str, payload: dict[str, Any]) -> None:
        async with self._lock:
            subscribers = list(self._local.get(channel_key, ()))
        for connection in subscribers:
            accepted = await connection.enqueue(payload)
            if not accepted:
                await connection.close(WS_CLOSE_OVERLOAD, "send queue overflow")
                await self.unsubscribe(channel_key, connection)

    async def _reaper(self) -> None:
        interval = max(1.0, settings.ws_pong_timeout_seconds / 2)
        max_silence = float(settings.ws_heartbeat_seconds + settings.ws_pong_timeout_seconds)
        try:
            while self._running:
                await asyncio.sleep(interval)
                if not self._running:
                    return
                now = time.monotonic()
                stale: set[Connection] = set()
                async with self._lock:
                    for subscribers in self._local.values():
                        for conn in subscribers:
                            if conn.is_stale(now, max_silence):
                                stale.add(conn)
                for conn in stale:
                    await self._reap_one(conn)
        except asyncio.CancelledError:
            raise

    async def _reap_one(self, connection: Connection) -> None:
        channel_keys: list[str] = []
        async with self._lock:
            for channel_key, subscribers in self._local.items():
                if connection in subscribers:
                    channel_keys.append(channel_key)
        for channel_key in channel_keys:
            await self.unsubscribe(channel_key, connection)
        await connection.close(WS_CLOSE_INTERNAL, "heartbeat lost")
        await logger.awarning("ws_connection_reaped", connection_id=connection.id)


_hub: Hub | None = None


def get_hub() -> Hub:
    if _hub is None:
        raise RuntimeError("Hub not started")
    return _hub


async def start_hub() -> None:
    global _hub
    if _hub is not None:
        return
    _hub = Hub()
    await _hub.start()


async def stop_hub() -> None:
    global _hub
    if _hub is not None:
        await _hub.stop()
        _hub = None
