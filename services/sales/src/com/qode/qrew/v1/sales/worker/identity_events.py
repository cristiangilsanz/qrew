"""Subscribes to identity events and updates user age and fingerprint context projections."""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any

import structlog

from com.qode.qrew.v1.sales.core.database import AsyncSessionLocal
from com.qode.qrew.v1.sales.repositories.projections import (
    FingerprintContextRepository,
    UserAgeContextRepository,
)

logger = structlog.get_logger(__name__)

STREAM = "IDENTITY"
DURABLE = "sales-identity-handler"


async def _parse(raw: bytes) -> dict[str, Any] | None:
    try:
        data = json.loads(raw.decode())
        assert isinstance(data, dict)
        return data  # type: ignore[return-value]
    except Exception:
        await logger.awarning("identity_events.parse_error")
        return None


async def handle_user_registered(raw: bytes) -> None:
    data = await _parse(raw)
    if data is None:
        return
    try:
        user_id = uuid.UUID(str(data["data"]["user_id"]))
        registered_at = datetime.fromisoformat(
            str(data["data"]["registered_at"])
        ).astimezone(timezone.utc)
    except (KeyError, ValueError):
        await logger.awarning("identity_events.user_registered.bad_payload")
        return
    async with AsyncSessionLocal() as session:
        await UserAgeContextRepository(session).upsert(
            user_id=user_id, registered_at=registered_at
        )
        await session.commit()
    await logger.ainfo("identity_events.user_age_upserted", user_id=str(user_id))


async def handle_fingerprint_seen(raw: bytes) -> None:
    data = await _parse(raw)
    if data is None:
        return
    try:
        fingerprint_hash = str(data["data"]["fingerprint_hash"])
        occurred_at = datetime.fromisoformat(
            str(data["data"]["occurred_at"])
        ).astimezone(timezone.utc)
    except (KeyError, ValueError):
        await logger.awarning("identity_events.fingerprint_seen.bad_payload")
        return
    async with AsyncSessionLocal() as session:
        await FingerprintContextRepository(session).seen(
            fingerprint_hash=fingerprint_hash, now=occurred_at
        )
        await session.commit()
    await logger.ainfo("identity_events.fingerprint_seen", hash=fingerprint_hash[:8])


_HANDLERS = {
    "identity.user.registered.v1": handle_user_registered,
    "identity.fingerprint.seen.v1": handle_fingerprint_seen,
}


async def run_identity_event_subscriber(nats_url: str) -> None:
    import nats
    from nats.js.api import ConsumerConfig, DeliverPolicy

    nc = await nats.connect(nats_url)  # type: ignore[reportUnknownMemberType]
    js = nc.jetstream()  # type: ignore[reportUnknownMemberType]

    try:
        await js.find_stream_name_by_subject("identity.>")
    except Exception:
        await js.add_stream(name=STREAM, subjects=["identity.>"])  # type: ignore[misc]

    for subject, handler in _HANDLERS.items():
        durable = f"{DURABLE}-{subject.replace('.', '-')}"
        config = ConsumerConfig(
            durable_name=durable,
            deliver_policy=DeliverPolicy.ALL,
            filter_subject=subject,
        )
        psub = await js.subscribe(
            subject, durable=durable, config=config, stream=STREAM
        )  # type: ignore[misc]
        await logger.ainfo("identity_events.subscribed", subject=subject)

        async def _consume(psub: Any = psub, h: Any = handler) -> None:
            async for msg in psub.messages:  # type: ignore[attr-defined]
                try:
                    await h(msg.data)  # type: ignore[attr-defined]
                    await msg.ack()  # type: ignore[attr-defined]
                except Exception:
                    await logger.awarning("identity_events.handler_error")
                    await msg.nak()  # type: ignore[attr-defined]

        asyncio.create_task(_consume())

    await logger.ainfo("identity_events.all_subscribed")
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass
    finally:
        await nc.drain()
