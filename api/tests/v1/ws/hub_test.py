import asyncio
from collections.abc import AsyncGenerator
from typing import Any

import fakeredis.aioredis
import pytest_asyncio

from com.qode.qrew.v1.service.core.ws import Hub


class _StubConnection:
    """Minimal connection stand-in for hub fan-out tests."""

    def __init__(self) -> None:
        self.received: list[dict[str, Any]] = []
        self.closed = False

    async def enqueue(self, message: dict[str, Any]) -> bool:
        self.received.append(message)
        return True

    async def close(self, *_args: Any, **_kwargs: Any) -> None:
        self.closed = True


@pytest_asyncio.fixture
async def hub() -> AsyncGenerator[Hub, None]:
    redis = fakeredis.aioredis.FakeRedis()
    h = Hub(redis)
    await h.start()
    yield h
    await h.stop()


async def test_subscribe_and_deliver_local(hub: Hub) -> None:
    conn = _StubConnection()
    await hub.subscribe("me.u1", conn)  # type: ignore[arg-type]
    await hub.deliver_local("me.u1", {"hello": "world"})
    assert conn.received == [{"hello": "world"}]


async def test_unsubscribe_stops_delivery(hub: Hub) -> None:
    conn = _StubConnection()
    await hub.subscribe("me.u1", conn)  # type: ignore[arg-type]
    await hub.unsubscribe("me.u1", conn)  # type: ignore[arg-type]
    await hub.deliver_local("me.u1", {"x": 1})
    assert conn.received == []


async def test_publish_round_trip_via_redis(hub: Hub) -> None:
    conn = _StubConnection()
    await hub.subscribe("me.u1", conn)  # type: ignore[arg-type]
    await hub.publish("me.u1", {"hello": "world"})
    for _ in range(40):
        if conn.received:
            break
        await asyncio.sleep(0.05)
    assert conn.received == [{"hello": "world"}]
