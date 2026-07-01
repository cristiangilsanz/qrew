import asyncio
import json
import uuid
from typing import Any

import structlog

from com.qode.qrew.v1.audit.worker.publisher import AUDIT_EVENTS_SUBJECT as SUBJECT
from com.qode.qrew.v1.audit.services.writer import AuditService

logger = structlog.get_logger(__name__)

STREAM = "AUDIT"
DURABLE = "audit-events-handler"


async def _parse(raw: bytes) -> dict[str, Any] | None:
    try:
        data = json.loads(raw.decode())
        assert isinstance(data, dict)
        return data  # type: ignore[return-value]
    except Exception as exc:
        await logger.awarning("audit_events.parse_error", error=repr(exc))
        return None


async def handle_audit_event(raw: bytes) -> None:
    envelope = await _parse(raw)
    if envelope is None:
        return

    d: dict[str, Any] = envelope.get("data", {})
    action = str(d.get("action", "unknown"))
    entity_type = d.get("entity_type") or None
    entity_id = d.get("entity_id") or None
    ip_address = d.get("ip_address") or None
    device_fingerprint_hash = d.get("device_fingerprint_hash") or None
    user_agent = d.get("user_agent") or None
    payload: dict[str, object] = d.get("payload") or {}

    actor_id: uuid.UUID | None = None
    raw_actor = envelope.get("actor_id") or d.get("actor_id")
    if raw_actor:
        try:
            actor_id = uuid.UUID(str(raw_actor))
        except ValueError:
            await logger.awarning("audit_events.invalid_actor_id", raw_actor=str(raw_actor))

    try:
        await AuditService().record(
            action=action,
            actor_id=actor_id,
            entity_type=entity_type,
            entity_id=entity_id,
            ip_address=ip_address,
            device_fingerprint_hash=device_fingerprint_hash,
            user_agent=user_agent,
            payload=payload,
        )
    except Exception as exc:
        await logger.awarning("audit_events.write_failed", action=action, error=repr(exc))
        raise


async def run_audit_event_subscriber(nats_url: str) -> None:
    import nats
    from nats.js.api import ConsumerConfig, DeliverPolicy

    nc = await nats.connect(nats_url)  # type: ignore[reportUnknownMemberType]
    js = nc.jetstream()  # type: ignore[reportUnknownMemberType]

    try:
        await js.find_stream_name_by_subject(SUBJECT)
    except Exception as exc:
        await logger.awarning("audit_events.stream_not_found", subject=SUBJECT, error=repr(exc))
        await js.add_stream(name=STREAM, subjects=["audit.>"])  # type: ignore[misc]

    config = ConsumerConfig(
        durable_name=DURABLE,
        deliver_policy=DeliverPolicy.ALL,
        filter_subject=SUBJECT,
    )
    psub = await js.subscribe(SUBJECT, durable=DURABLE, config=config, stream=STREAM)  # type: ignore[misc]
    await logger.ainfo("audit_events.subscribed", subject=SUBJECT)

    async def _consume() -> None:
        async for msg in psub.messages:  # type: ignore[attr-defined]
            try:
                await handle_audit_event(msg.data)  # type: ignore[attr-defined]
                await msg.ack()  # type: ignore[attr-defined]
            except Exception as exc:
                await logger.awarning("audit_events.handler_error", error=repr(exc))
                await msg.nak()  # type: ignore[attr-defined]

    _task = asyncio.create_task(_consume())

    await logger.ainfo("audit_events.subscriber_ready")
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        _task.cancel()
        try:
            await _task
        except asyncio.CancelledError:
            pass
    finally:
        try:
            await nc.drain()
        except Exception as exc:
            await logger.awarning("audit_events.drain_failed", error=repr(exc))
