import asyncio
import contextlib
from unittest.mock import AsyncMock, MagicMock

from starlette.websockets import WebSocketState

from com.qode.qrew.v1.service.core.ws import Connection


def _socket() -> MagicMock:
    sock = MagicMock()
    sock.application_state = WebSocketState.CONNECTED
    sock.send_json = AsyncMock()
    sock.close = AsyncMock()
    return sock


async def test_enqueue_returns_false_when_buffer_full() -> None:
    conn = Connection(
        socket=_socket(), user=MagicMock(), session=MagicMock(), queue_size=2
    )
    assert await conn.enqueue({"a": 1}) is True
    assert await conn.enqueue({"b": 2}) is True
    assert await conn.enqueue({"c": 3}) is False


async def test_close_only_runs_once() -> None:
    sock = _socket()
    conn = Connection(socket=sock, user=MagicMock(), session=MagicMock())
    await conn.close()
    await conn.close()
    assert sock.close.await_count == 1


async def test_writer_sends_messages_until_closed() -> None:
    sock = _socket()
    conn = Connection(socket=sock, user=MagicMock(), session=MagicMock())
    await conn.enqueue({"hello": "world"})
    task = asyncio.create_task(conn.writer())
    await asyncio.sleep(0.05)
    await conn.close()
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError, Exception):
        await task
    sock.send_json.assert_any_await({"hello": "world"})
