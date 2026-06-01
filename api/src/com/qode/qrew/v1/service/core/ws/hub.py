import asyncio
import contextlib
import json
from typing import Any

import redis.asyncio as aioredis
import structlog

from com.qode.qrew.v1.service.core.ws.close_codes import WS_CLOSE_OVERLOAD
from com.qode.qrew.v1.service.core.ws.connection import Connection

logger = structlog.get_logger(__name__)

_REDIS_PREFIX = "ws"


def _redis_channel(channel_key: str) -> str:
    return f"{_REDIS_PREFIX}:{channel_key}"


class Hub:
    """Process-wide WebSocket subscriber index backed by Redis pub/sub."""

    def __init__(self, redis_client: aioredis.Redis) -> None:  # type: ignore[type-arg]
        self._redis = redis_client
        self._local: dict[str, set[Connection]] = {}
        self._pubsub: Any = None
        self._task: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()
        self._running = False

    async def start(self) -> None:
        if self._running:
            return
        self._pubsub = self._redis.pubsub()  # type: ignore[misc]
        self._running = True
        self._task = asyncio.create_task(self._dispatcher())

    async def stop(self) -> None:
        self._running = False
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await self._task
            self._task = None
        if self._pubsub is not None:
            with contextlib.suppress(Exception):
                await self._pubsub.aclose()  # type: ignore[misc]
            self._pubsub = None
        connections = {c for conns in self._local.values() for c in conns}
        for connection in connections:
            await connection.close(1001, "shutdown")
        self._local.clear()

    async def subscribe(self, channel_key: str, connection: Connection) -> None:
        async with self._lock:
            subscribers = self._local.setdefault(channel_key, set())
            first = not subscribers
            subscribers.add(connection)
        if first and self._pubsub is not None:
            await self._pubsub.subscribe(_redis_channel(channel_key))  # type: ignore[misc]

    async def unsubscribe(self, channel_key: str, connection: Connection) -> None:
        empty = False
        async with self._lock:
            subscribers = self._local.get(channel_key)
            if subscribers is None:
                return
            subscribers.discard(connection)
            if not subscribers:
                self._local.pop(channel_key, None)
                empty = True
        if empty and self._pubsub is not None:
            await self._pubsub.unsubscribe(_redis_channel(channel_key))  # type: ignore[misc]

    async def publish(self, channel_key: str, payload: dict[str, Any]) -> None:
        try:
            await self._redis.publish(_redis_channel(channel_key), json.dumps(payload))  # type: ignore[misc]
        except aioredis.RedisError as exc:
            await logger.awarning("ws_publish_failed", error=repr(exc))

    async def deliver_local(self, channel_key: str, payload: dict[str, Any]) -> None:
        """Hand a payload to every local subscriber of the channel."""
        subscribers = list(self._local.get(channel_key, ()))
        for connection in subscribers:
            accepted = await connection.enqueue(payload)
            if not accepted:
                await connection.close(WS_CLOSE_OVERLOAD, "send queue overflow")
                await self.unsubscribe(channel_key, connection)

    async def _dispatcher(self) -> None:
        assert self._pubsub is not None
        try:
            while self._running:
                try:
                    message = await self._pubsub.get_message(  # type: ignore[misc]
                        ignore_subscribe_messages=True, timeout=1.0
                    )
                except Exception as exc:
                    await logger.awarning("ws_dispatcher_error", error=repr(exc))
                    await asyncio.sleep(0.5)
                    continue
                if message is None:
                    continue
                message_dict: dict[str, Any] = message  # type: ignore[assignment]
                redis_channel_raw: Any = message_dict.get("channel")  # type: ignore[misc]
                redis_channel: str | None = None
                if isinstance(redis_channel_raw, bytes):
                    redis_channel = redis_channel_raw.decode()
                elif isinstance(redis_channel_raw, str):
                    redis_channel = redis_channel_raw
                if redis_channel is None or not redis_channel.startswith(
                    f"{_REDIS_PREFIX}:"
                ):
                    continue
                channel_key = redis_channel[len(f"{_REDIS_PREFIX}:") :]
                data_raw: Any = message_dict.get("data")  # type: ignore[misc]
                data: str | None = None
                if isinstance(data_raw, bytes):
                    data = data_raw.decode()
                elif isinstance(data_raw, str):
                    data = data_raw
                if data is None:
                    continue
                try:
                    parsed: Any = json.loads(data)
                except json.JSONDecodeError:
                    continue
                if not isinstance(parsed, dict):
                    continue
                payload: dict[str, Any] = dict(parsed)  # type: ignore[arg-type]
                await self.deliver_local(channel_key, payload)
        except asyncio.CancelledError:
            raise
