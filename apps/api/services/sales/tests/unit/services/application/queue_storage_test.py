# tests that the queue score keeps its random tail once redis has stored it
import uuid
from collections.abc import AsyncIterator
from typing import Any

import fakeredis.aioredis
import pytest

from com.qode.qrew.v1.sales.services.application.queue import storage

_NOW_MS = 1_788_701_086_917  # a millisecond well inside the service's lifetime
_FOURTEEN_YEARS_MS = 14 * 365 * 24 * 60 * 60 * 1000


# points the queue at a fake redis that stores scores as doubles, the way redis does
@pytest.fixture
async def redis() -> AsyncIterator[Any]:
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    storage._ClientState.client = client
    yield client
    storage._ClientState.client = None
    await client.aclose()


# joins a user with the entropy the caller supplies and nothing else
def _no_extra_entropy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(storage.secrets, "randbits", lambda _bits: 0)


class TestScore:
    # verifies that the score fits in the mantissa a sorted set stores it in
    def test_fits_in_the_exact_integer_range(self) -> None:
        score = storage._score_for(_NOW_MS, 0xFFFF)
        assert score < storage.MAX_EXACT_SCORE
        assert float(score) == score

    # verifies that the score still fits years from now
    def test_still_fits_fourteen_years_from_now(self) -> None:
        score = storage._score_for(_NOW_MS + _FOURTEEN_YEARS_MS, 0xFFFF)
        assert score < storage.MAX_EXACT_SCORE
        assert float(score) == score

    # verifies that the old packing it replaced did not fit
    def test_the_packing_it_replaced_did_not_fit(self) -> None:
        old = (_NOW_MS << 32) | (0xABCD << 16) | 0xFFFF
        assert old > storage.MAX_EXACT_SCORE
        assert float(old) != old

    # verifies that a later millisecond always sorts after an earlier one
    def test_a_later_millisecond_always_scores_higher(self) -> None:
        earliest = storage._score_for(_NOW_MS, 0xFFFF)
        latest = storage._score_for(_NOW_MS + 1, 0x0000)
        assert latest > earliest

    # verifies that the caller's tiebreak is not the only source of randomness
    def test_mixes_fresh_entropy_into_the_callers_tiebreak(self) -> None:
        scores = {storage._score_for(_NOW_MS, 7) for _ in range(64)}
        assert len(scores) > 1


class TestJoinQueue:
    # verifies that redis reads the score back exactly as it was written
    async def test_redis_stores_the_score_without_rounding(
        self, redis: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _no_extra_entropy(monkeypatch)
        event_id = uuid.uuid4()
        user_id = uuid.uuid4()
        await storage.join_queue(
            event_id=event_id,
            user_id=user_id,
            sale_start_ms=_NOW_MS,
            now_ms=_NOW_MS,
            tiebreak=0x5AB3,
        )
        stored = await redis.zscore(f"queue:event:{event_id}", str(user_id))
        assert int(stored) == storage._score_for(_NOW_MS, 0x5AB3)

    # verifies that entrants of the same millisecond keep distinct stored scores
    async def test_distinct_tiebreaks_survive_the_write(
        self, redis: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _no_extra_entropy(monkeypatch)
        event_id = uuid.uuid4()
        members: list[tuple[uuid.UUID, int]] = []
        for tiebreak in range(64):
            user_id = uuid.uuid4()
            members.append((user_id, tiebreak))
            await storage.join_queue(
                event_id=event_id,
                user_id=user_id,
                sale_start_ms=_NOW_MS,
                now_ms=_NOW_MS,
                tiebreak=tiebreak,
            )
        stored = {
            await redis.zscore(f"queue:event:{event_id}", str(user_id)) for user_id, _ in members
        }
        assert len(stored) == 64

    # verifies that the tiebreak, not the user id, decides the order within a millisecond
    async def test_the_order_follows_the_tiebreak_not_the_user_id(
        self, redis: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _no_extra_entropy(monkeypatch)
        event_id = uuid.uuid4()
        first = uuid.UUID("ffffffff-ffff-4fff-8fff-ffffffffffff")
        second = uuid.UUID("00000000-0000-4000-8000-000000000000")
        await storage.join_queue(
            event_id=event_id,
            user_id=first,
            sale_start_ms=_NOW_MS,
            now_ms=_NOW_MS,
            tiebreak=1,
        )
        await storage.join_queue(
            event_id=event_id,
            user_id=second,
            sale_start_ms=_NOW_MS,
            now_ms=_NOW_MS,
            tiebreak=2,
        )
        order = await redis.zrange(f"queue:event:{event_id}", 0, -1)
        assert order == [str(first), str(second)]

    # verifies that an entrant of an earlier millisecond still goes first
    async def test_an_earlier_millisecond_still_goes_first(self, redis: Any) -> None:
        event_id = uuid.uuid4()
        early = uuid.uuid4()
        late = uuid.uuid4()
        await storage.join_queue(
            event_id=event_id,
            user_id=early,
            sale_start_ms=0,
            now_ms=_NOW_MS,
            tiebreak=0xFFFF,
        )
        await storage.join_queue(
            event_id=event_id,
            user_id=late,
            sale_start_ms=0,
            now_ms=_NOW_MS + 1,
            tiebreak=0x0000,
        )
        order = await redis.zrange(f"queue:event:{event_id}", 0, -1)
        assert order == [str(early), str(late)]
