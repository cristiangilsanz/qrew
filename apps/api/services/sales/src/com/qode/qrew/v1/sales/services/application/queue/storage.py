import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import redis.asyncio as aioredis
import structlog

from com.qode.qrew.v1.sales.core import principals as jwt_keys
from observability import traced
from com.qode.qrew.v1.sales.core.config import settings as _settings

logger = structlog.get_logger(__name__)

_QUEUE_KEY = "queue:event:{event_id}"
_REDEEMED_KEY = "queue:redeemed:{event_id}"
_RESERVATION_KEY = "queue:reservation:{event_id}"
_REDEEM_TOKEN_KEY = "queue:redeem_token:{event_id}:{user_id}"

REDEEM_SCOPE = "queue.redeem"
RESERVATION_SCOPE = "queue.reservation"


@dataclass(frozen=True)
class JoinResult:
    position: int


@dataclass(frozen=True)
class AdmittedSlot:
    user_id: str
    redeem_token: str
    jti: str


class _ClientState:
    client: aioredis.Redis | None = None  # type: ignore[type-arg]


def _shared_client() -> aioredis.Redis:  # type: ignore[type-arg]
    if _ClientState.client is None:
        _ClientState.client = aioredis.from_url(  # type: ignore[type-arg]
            _settings.redis_url, decode_responses=True
        )
    return _ClientState.client


async def close_queue() -> None:
    if _ClientState.client is not None:
        await _ClientState.client.aclose()
    _ClientState.client = None


def _score_for(now_ms: int, tiebreak: int) -> int:
    rand = secrets.randbits(16)
    return (now_ms << 32) | (rand << 16) | (tiebreak & 0xFFFF)


@traced("queue.join")
async def join_queue(
    *,
    event_id: uuid.UUID,
    user_id: uuid.UUID,
    sale_start_ms: int,
    now_ms: int,
    tiebreak: int,
) -> JoinResult | None:
    """ZADD NX the user; return position or None if already in the queue."""
    redis = _shared_client()
    key = _QUEUE_KEY.format(event_id=event_id)
    score_base = max(sale_start_ms, now_ms)
    score = _score_for(score_base, tiebreak)
    added = await redis.zadd(key, {str(user_id): score}, nx=True)  # type: ignore[misc]
    if not added:
        return None
    rank = await redis.zrank(key, str(user_id))  # type: ignore[misc]
    if rank is None:
        return None
    return JoinResult(position=int(rank) + 1)


@traced("queue.position")
async def queue_position(event_id: uuid.UUID, user_id: uuid.UUID) -> int | None:
    """Return 1-based position, or None if not in queue."""
    redis = _shared_client()
    rank = await redis.zrank(_QUEUE_KEY.format(event_id=event_id), str(user_id))  # type: ignore[misc]
    return None if rank is None else int(rank) + 1


def _build_redeem_token(*, event_id: uuid.UUID, user_id: str) -> tuple[str, str]:
    now = datetime.now(UTC)
    jti = uuid.uuid4().hex
    payload: dict[str, Any] = {
        "sub": user_id,
        "scope": REDEEM_SCOPE,
        "event_id": str(event_id),
        "jti": jti,
        "iat": now,
        "exp": now + timedelta(seconds=_settings.queue_redeem_window_seconds),
    }
    return jwt_keys.sign(jwt_keys.Purpose.QUEUE, payload), jti


def _build_reservation_token(*, event_id: uuid.UUID, user_id: str) -> tuple[str, str]:
    now = datetime.now(UTC)
    jti = uuid.uuid4().hex
    payload: dict[str, Any] = {
        "sub": user_id,
        "scope": RESERVATION_SCOPE,
        "event_id": str(event_id),
        "jti": jti,
        "iat": now,
        "exp": now + timedelta(seconds=_settings.queue_reservation_window_seconds),
    }
    return jwt_keys.sign(jwt_keys.Purpose.QUEUE, payload), jti


@traced("queue.admit")
async def admit_batch(*, event_id: uuid.UUID, batch_size: int) -> list[AdmittedSlot]:
    if batch_size <= 0:
        return []
    redis = _shared_client()
    key = _QUEUE_KEY.format(event_id=event_id)
    members = await redis.zrange(key, 0, batch_size - 1)  # type: ignore[misc]
    if not members:
        return []
    await redis.zrem(key, *members)  # type: ignore[misc]
    admitted: list[AdmittedSlot] = []
    for raw in members:
        user_id = raw if isinstance(raw, str) else raw.decode()
        token, jti = _build_redeem_token(event_id=event_id, user_id=user_id)
        key = _REDEEM_TOKEN_KEY.format(event_id=event_id, user_id=user_id)
        await redis.set(key, token, ex=_settings.queue_redeem_window_seconds)  # type: ignore[misc]
        admitted.append(AdmittedSlot(user_id=user_id, redeem_token=token, jti=jti))
    return admitted


@traced("queue.get_redeem_token")
async def get_redeem_token(event_id: uuid.UUID, user_id: uuid.UUID) -> str | None:
    """Return the stored redeem token for an admitted user, or None."""
    redis = _shared_client()
    key = _REDEEM_TOKEN_KEY.format(event_id=event_id, user_id=user_id)
    return await redis.get(key)  # type: ignore[no-any-return]


@traced("queue.redeem")
async def redeem_window_token(*, token: str, user_id: uuid.UUID) -> str:
    """Verify the redeem token (single-use), return a reservation_window_token."""
    from jwt import InvalidTokenError

    payload = jwt_keys.verify(jwt_keys.Purpose.QUEUE, token)
    if payload.get("scope") != REDEEM_SCOPE:
        raise InvalidTokenError("Unexpected scope")
    if payload.get("sub") != str(user_id):
        raise InvalidTokenError("Subject mismatch")
    event_raw = payload.get("event_id")
    if not isinstance(event_raw, str):
        raise InvalidTokenError("event_id missing")
    event_id = uuid.UUID(event_raw)
    jti = payload.get("jti")
    if not isinstance(jti, str):
        raise InvalidTokenError("jti missing")
    redis = _shared_client()
    added = await redis.sadd(_REDEEMED_KEY.format(event_id=event_id), jti)  # type: ignore[misc]
    if not added:
        raise InvalidTokenError("Token already redeemed")
    reservation_token, _ = _build_reservation_token(event_id=event_id, user_id=str(user_id))
    return reservation_token


@traced("queue.consume_reservation")
async def consume_reservation_token(*, token: str, user_id: uuid.UUID) -> uuid.UUID:
    """Verify and one-shot-consume a reservation_window_token; return its event_id."""
    from jwt import InvalidTokenError

    payload = jwt_keys.verify(jwt_keys.Purpose.QUEUE, token)
    if payload.get("scope") != RESERVATION_SCOPE:
        raise InvalidTokenError("Unexpected scope")
    if payload.get("sub") != str(user_id):
        raise InvalidTokenError("Subject mismatch")
    event_raw = payload.get("event_id")
    if not isinstance(event_raw, str):
        raise InvalidTokenError("event_id missing")
    event_id = uuid.UUID(event_raw)
    jti = payload.get("jti")
    if not isinstance(jti, str):
        raise InvalidTokenError("jti missing")
    redis = _shared_client()
    added = await redis.sadd(  # type: ignore[misc]
        _RESERVATION_KEY.format(event_id=event_id), jti
    )
    if not added:
        raise InvalidTokenError("Token already consumed")
    return event_id
