# writes the admission queues into redis the way the sales service reads them

from __future__ import annotations

import secrets

import redis.asyncio as aioredis

from ..core import SeedConfig, Timeline
from ..data import Dataset

NAME = "queues"

_QUEUE_KEY = "queue:event:{event_id}"


# builds the score that orders a queue by join time then by tiebreak
def _score(joined_ms: int, tiebreak: int) -> int:
    rand = secrets.randbits(16)
    return (joined_ms << 32) | (rand << 16) | (tiebreak & 0xFFFF)


# clears every seeded queue and writes its members in order
async def write(data: Dataset, when: Timeline, cfg: SeedConfig) -> None:
    redis = aioredis.from_url(cfg.redis_url)
    try:
        event_ids = {data.event(key).id for key, _, _ in data.admission_queue}
        for event_id in event_ids:
            await redis.delete(_QUEUE_KEY.format(event_id=event_id))
        for position, (event_key, person_key, tiebreak) in enumerate(
            data.admission_queue
        ):
            joined = when.minutes(-30 + position)
            member = str(data.person(person_key).id)
            await redis.zadd(
                _QUEUE_KEY.format(event_id=data.event(event_key).id),
                {member: _score(int(joined.timestamp() * 1000), tiebreak)},
            )
    finally:
        await redis.aclose()
