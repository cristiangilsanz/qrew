from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.websockets import WebSocketState

from com.qode.qrew.v1.gateway.hub.connection import Connection
from com.qode.qrew.v1.gateway.hub.hub import Hub


def _make_socket(state: WebSocketState = WebSocketState.CONNECTED) -> MagicMock:
    ws = MagicMock()
    ws.application_state = state
    ws.send_json = AsyncMock()
    ws.close = AsyncMock()
    return ws


async def _make_connection(queue_size: int = 64) -> Connection:
    ws = _make_socket()
    return Connection(socket=ws, claims={}, queue_size=queue_size)


@pytest.mark.asyncio
async def test_subscribe_and_deliver() -> None:
    hub = Hub()
    await hub.start()
    try:
        conn = await _make_connection()
        await hub.subscribe("me.user-1", conn)
        await hub.deliver("me.user-1", {"type": "hello"})
        assert not conn._queue.empty()
        msg = conn._queue.get_nowait()
        assert msg["type"] == "hello"
    finally:
        await hub.stop()


@pytest.mark.asyncio
async def test_unsubscribe_removes_connection() -> None:
    hub = Hub()
    await hub.start()
    try:
        conn = await _make_connection()
        await hub.subscribe("me.user-2", conn)
        await hub.unsubscribe("me.user-2", conn)
        await hub.deliver("me.user-2", {"type": "ghost"})
        assert conn._queue.empty()
    finally:
        await hub.stop()


@pytest.mark.asyncio
async def test_deliver_closes_overloaded_connection() -> None:
    hub = Hub()
    await hub.start()
    try:
        conn = await _make_connection(queue_size=1)
        await hub.subscribe("me.user-3", conn)
        # Fill the queue so next enqueue returns False
        await conn.enqueue({"type": "fill"})
        # Deliver should detect overload and close
        await hub.deliver("me.user-3", {"type": "overflow"})
        assert conn.closed
    finally:
        await hub.stop()


@pytest.mark.asyncio
async def test_stop_closes_all_connections() -> None:
    hub = Hub()
    await hub.start()
    conn = await _make_connection()
    await hub.subscribe("me.user-4", conn)
    await hub.stop()
    assert conn.closed


@pytest.mark.asyncio
async def test_deliver_to_empty_channel_is_noop() -> None:
    hub = Hub()
    await hub.start()
    try:
        await hub.deliver("me.nobody", {"type": "ignored"})
    finally:
        await hub.stop()
