import time
from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.websockets import WebSocketState

from com.qode.qrew.v1.gateway.hub.connection import Connection
from com.qode.qrew.v1.gateway.hub.close_codes import WS_CLOSE_NORMAL


def _make_connection(
    queue_size: int = 4, state: WebSocketState = WebSocketState.CONNECTED
) -> Connection:
    ws = MagicMock()
    ws.application_state = state
    ws.send_json = AsyncMock()
    ws.close = AsyncMock()
    return Connection(socket=ws, claims={}, queue_size=queue_size)


@pytest.mark.asyncio
async def test_enqueue_returns_true_when_space() -> None:
    conn = _make_connection()
    result = await conn.enqueue({"type": "msg"})
    assert result is True


@pytest.mark.asyncio
async def test_enqueue_returns_false_when_full() -> None:
    conn = _make_connection(queue_size=1)
    await conn.enqueue({"type": "first"})
    result = await conn.enqueue({"type": "overflow"})
    assert result is False


@pytest.mark.asyncio
async def test_enqueue_returns_false_when_closed() -> None:
    conn = _make_connection()
    await conn.close()
    result = await conn.enqueue({"type": "msg"})
    assert result is False


def test_is_stale_returns_true_after_timeout() -> None:
    conn = _make_connection()
    conn._last_pong = time.monotonic() - 100.0
    assert conn.is_stale(time.monotonic(), max_silence_seconds=30.0) is True


def test_is_stale_returns_false_when_recent() -> None:
    conn = _make_connection()
    conn._last_pong = time.monotonic()
    assert conn.is_stale(time.monotonic(), max_silence_seconds=30.0) is False


@pytest.mark.asyncio
async def test_close_sets_closed() -> None:
    conn = _make_connection()
    assert conn.closed is False
    await conn.close(WS_CLOSE_NORMAL)
    assert conn.closed is True


@pytest.mark.asyncio
async def test_close_is_idempotent() -> None:
    conn = _make_connection()
    await conn.close()
    await conn.close()
    assert conn.closed is True


def test_record_pong_updates_last_pong() -> None:
    conn = _make_connection()
    old = conn._last_pong
    now = time.monotonic() + 10.0
    conn.record_pong(now)
    assert conn._last_pong == now
    assert conn._last_pong > old
