import uuid
from typing import Any

import fakeredis.aioredis
import jwt
import pytest
import pytest_asyncio

from com.qode.qrew.v1.service.core.queue import queue as queue_module
from com.qode.qrew.v1.service.core.queue import (
    admit_batch,
    consume_reservation_token,
    join_queue,
    queue_position,
    redeem_window_token,
)


@pytest_asyncio.fixture(autouse=True)
async def _fake_redis() -> Any:  # pyright: ignore[reportUnusedFunction]
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    queue_module._ClientState.client = fake  # pyright: ignore[reportPrivateUsage]
    try:
        yield fake
    finally:
        await fake.aclose()
        queue_module._ClientState.client = None  # pyright: ignore[reportPrivateUsage]


async def test_join_assigns_first_then_second_position() -> None:
    event_id = uuid.uuid4()
    user_a = uuid.uuid4()
    user_b = uuid.uuid4()
    a = await join_queue(
        event_id=event_id,
        user_id=user_a,
        sale_start_ms=1_000_000,
        now_ms=1_000_000,
        tiebreak=0,
    )
    b = await join_queue(
        event_id=event_id,
        user_id=user_b,
        sale_start_ms=1_000_000,
        now_ms=2_000_000,
        tiebreak=1,
    )
    assert a is not None and a.position == 1
    assert b is not None and b.position == 2


async def test_double_join_is_rejected() -> None:
    event_id = uuid.uuid4()
    user_id = uuid.uuid4()
    first = await join_queue(
        event_id=event_id,
        user_id=user_id,
        sale_start_ms=1_000_000,
        now_ms=1_000_000,
        tiebreak=0,
    )
    second = await join_queue(
        event_id=event_id,
        user_id=user_id,
        sale_start_ms=1_000_000,
        now_ms=1_000_000,
        tiebreak=0,
    )
    assert first is not None
    assert second is None


async def test_position_reads_rank() -> None:
    event_id = uuid.uuid4()
    user_a = uuid.uuid4()
    user_b = uuid.uuid4()
    await join_queue(
        event_id=event_id,
        user_id=user_a,
        sale_start_ms=1_000_000,
        now_ms=1_000_000,
        tiebreak=0,
    )
    await join_queue(
        event_id=event_id,
        user_id=user_b,
        sale_start_ms=1_000_000,
        now_ms=2_000_000,
        tiebreak=1,
    )
    assert await queue_position(event_id, user_a) == 1
    assert await queue_position(event_id, user_b) == 2
    assert await queue_position(event_id, uuid.uuid4()) is None


async def test_admit_batch_pops_head() -> None:
    event_id = uuid.uuid4()
    users = [uuid.uuid4() for _ in range(5)]
    for i, user in enumerate(users):
        await join_queue(
            event_id=event_id,
            user_id=user,
            sale_start_ms=1_000_000,
            now_ms=1_000_000 + i,
            tiebreak=i,
        )
    admitted = await admit_batch(event_id=event_id, batch_size=3)
    assert len(admitted) == 3
    admitted_user_ids = {slot.user_id for slot in admitted}
    assert admitted_user_ids == {str(u) for u in users[:3]}
    # Remaining users still in queue
    assert await queue_position(event_id, users[3]) == 1
    assert await queue_position(event_id, users[4]) == 2


async def test_redeem_then_reserve_one_shot() -> None:
    event_id = uuid.uuid4()
    user_id = uuid.uuid4()
    await join_queue(
        event_id=event_id,
        user_id=user_id,
        sale_start_ms=1_000_000,
        now_ms=1_000_000,
        tiebreak=0,
    )
    admitted = await admit_batch(event_id=event_id, batch_size=1)
    assert admitted
    reservation_token = await redeem_window_token(
        token=admitted[0].redeem_token, user_id=user_id
    )
    with pytest.raises(jwt.InvalidTokenError):
        await redeem_window_token(token=admitted[0].redeem_token, user_id=user_id)
    event_back = await consume_reservation_token(
        token=reservation_token, user_id=user_id
    )
    assert event_back == event_id
    with pytest.raises(jwt.InvalidTokenError):
        await consume_reservation_token(token=reservation_token, user_id=user_id)


async def test_redeem_rejects_wrong_subject() -> None:
    event_id = uuid.uuid4()
    user_id = uuid.uuid4()
    stranger = uuid.uuid4()
    await join_queue(
        event_id=event_id,
        user_id=user_id,
        sale_start_ms=1_000_000,
        now_ms=1_000_000,
        tiebreak=0,
    )
    admitted = await admit_batch(event_id=event_id, batch_size=1)
    with pytest.raises(jwt.InvalidTokenError):
        await redeem_window_token(token=admitted[0].redeem_token, user_id=stranger)
