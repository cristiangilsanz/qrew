import time
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import MagicMock

import fakeredis.aioredis
import pytest_asyncio

from com.qode.qrew.v1.service.core.ws import Hub
from com.qode.qrew.v1.service.core.ws.connection import Connection
from com.qode.qrew.v1.service.settings import settings


class _StubSocket:
    def __init__(self) -> None:
        from starlette.websockets import WebSocketState

        self.application_state = WebSocketState.CONNECTED
        self.closed_with: tuple[int, str] | None = None

    async def send_json(self, _message: dict[str, Any]) -> None:
        return None

    async def close(self, code: int = 1000, reason: str = "") -> None:
        from starlette.websockets import WebSocketState

        self.closed_with = (code, reason)
        self.application_state = WebSocketState.DISCONNECTED


def _make_connection(last_pong: float) -> Connection:
    conn = Connection(
        socket=_StubSocket(),  # type: ignore[arg-type]
        user=MagicMock(id="u-1"),
        session=MagicMock(),
    )
    conn.record_pong(last_pong)
    return conn


@pytest_asyncio.fixture
async def hub() -> AsyncGenerator[Hub, None]:
    redis = fakeredis.aioredis.FakeRedis()
    h = Hub(redis)
    await h.start()
    yield h
    await h.stop()


async def test_reap_stale_closes_silent_connection(hub: Hub) -> None:
    grace = settings.ws_heartbeat_seconds + settings.ws_pong_timeout_seconds
    stale = _make_connection(time.monotonic() - grace - 5)
    await hub.subscribe("me.u1", stale)

    reaped = await hub.reap_stale()
    assert reaped == 1
    assert stale.closed
    assert hub._local.get("me.u1") is None  # pyright: ignore[reportPrivateUsage]


async def test_reap_stale_leaves_healthy_connection_alone(hub: Hub) -> None:
    healthy = _make_connection(time.monotonic())
    await hub.subscribe("me.u1", healthy)

    reaped = await hub.reap_stale()
    assert reaped == 0
    assert not healthy.closed
    subscribers = hub._local.get("me.u1")  # pyright: ignore[reportPrivateUsage]
    assert subscribers is not None
    assert healthy in subscribers


async def test_reap_stale_unsubscribes_from_every_channel_held(hub: Hub) -> None:
    grace = settings.ws_heartbeat_seconds + settings.ws_pong_timeout_seconds
    stale = _make_connection(time.monotonic() - grace - 1)
    await hub.subscribe("me.u1", stale)
    await hub.subscribe("queue.event.42", stale)

    await hub.reap_stale()

    assert hub._local.get("me.u1") is None  # pyright: ignore[reportPrivateUsage]
    assert hub._local.get("queue.event.42") is None  # pyright: ignore[reportPrivateUsage]


async def test_connection_is_stale_uses_grace_window() -> None:
    conn = _make_connection(time.monotonic() - 100)
    assert conn.is_stale(time.monotonic(), max_silence_seconds=50)
    assert not conn.is_stale(time.monotonic(), max_silence_seconds=200)
