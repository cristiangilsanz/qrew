import asyncio
import json
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog

from com.qode.qrew.v1.ticketing.services.audit import AuditService
from com.qode.qrew.v1.ticketing.core.database import AsyncSessionLocal
from com.qode.qrew.v1.ticketing.models.ticket import TicketState
from com.qode.qrew.v1.ticketing.repositories.projections import DeviceContextRepository
from com.qode.qrew.v1.ticketing.repositories.ticket import TicketRepository
from com.qode.qrew.v1.ticketing.services.ticket.transition import transition_ticket

logger = structlog.get_logger(__name__)

STREAM = "IDENTITY"
DURABLE = "ticketing-identity-handler"

_TICKET_FROZEN_DEVICE_REVOKE = "TICKET_FROZEN_DEVICE_REVOKE"


async def _parse(raw: bytes) -> dict[str, Any] | None:
    try:
        data = json.loads(raw.decode())
        assert isinstance(data, dict)
        return data  # type: ignore[return-value]
    except Exception as exc:
        await logger.awarning("identity_events.parse_error", error=repr(exc))
        return None


async def handle_device_attested(raw: bytes) -> None:
    data = await _parse(raw)
    if data is None:
        return
    try:
        device_id = uuid.UUID(str(data["data"]["device_id"]))
        user_id = uuid.UUID(str(data["data"]["user_id"]))
        attested_at = datetime.fromisoformat(str(data["data"]["attested_at"]))
    except (KeyError, ValueError):
        await logger.awarning("identity_events.device_attested.bad_payload")
        return
    async with AsyncSessionLocal() as session:
        await DeviceContextRepository(session).upsert(
            device_id=device_id,
            user_id=user_id,
            attested_at=attested_at,
            revoked_at=None,
        )
        await session.commit()
    await logger.ainfo("identity_events.device_attested", device_id=str(device_id))


async def handle_device_revoked(raw: bytes) -> None:
    data = await _parse(raw)
    if data is None:
        return
    try:
        device_id = uuid.UUID(str(data["data"]["device_id"]))
        user_id = uuid.UUID(str(data["data"]["user_id"]))
    except (KeyError, ValueError):
        await logger.awarning("identity_events.device_revoked.bad_payload")
        return

    revoked_at = datetime.now(UTC)
    async with AsyncSessionLocal() as session:
        device_repo = DeviceContextRepository(session)
        existing = await device_repo.get_by_device_id(device_id)
        await device_repo.upsert(
            device_id=device_id,
            user_id=user_id,
            attested_at=existing.attested_at if existing else None,
            revoked_at=revoked_at,
        )
        audit = AuditService()
        tickets = await TicketRepository(session).list_by_user_device_state(
            user_id, device_id, TicketState.issued
        )
        for ticket in tickets:
            await transition_ticket(
                session,
                ticket_id=ticket.id,
                to_state=TicketState.frozen,
                reason="device_revoked",
                actor_id=user_id,
                audit=audit,
            )
            try:
                await audit.record(
                    action=_TICKET_FROZEN_DEVICE_REVOKE,
                    actor_id=user_id,
                    entity_type="ticket",
                    entity_id=str(ticket.id),
                    payload={"device_id": str(device_id)},
                )
            except Exception as exc:
                await logger.awarning(
                    "identity_events.audit_failed",
                    action=_TICKET_FROZEN_DEVICE_REVOKE,
                    ticket_id=str(ticket.id),
                    error=repr(exc),
                )
        await session.commit()
    await logger.ainfo(
        "identity_events.device_revoked",
        device_id=str(device_id),
        tickets_frozen=len(tickets),
    )


_HANDLERS = {
    "identity.device.attested.v1": handle_device_attested,
    "identity.device.revoked.v1": handle_device_revoked,
}


async def run_identity_event_subscriber(nats_url: str) -> None:
    import nats
    from nats.js.api import ConsumerConfig, DeliverPolicy

    _tasks: list[asyncio.Task[None]] = []
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
        psub = await js.subscribe(subject, durable=durable, config=config, stream=STREAM)  # type: ignore[misc]
        await logger.ainfo("identity_events.subscribed", subject=subject)

        async def _consume(psub: Any = psub, h: Any = handler) -> None:
            try:
                async for msg in psub.messages:  # type: ignore[attr-defined]
                    try:
                        await h(msg.data)  # type: ignore[attr-defined]
                        await msg.ack()  # type: ignore[attr-defined]
                    except Exception as exc:
                        await logger.awarning("identity_events.handler_error", error=repr(exc))
                        await msg.nak()  # type: ignore[attr-defined]
            except asyncio.CancelledError:
                raise

        _tasks.append(asyncio.create_task(_consume()))

    await logger.ainfo("identity_events.all_subscribed")
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass
    finally:
        for t in _tasks:
            t.cancel()
        await asyncio.gather(*_tasks, return_exceptions=True)
        try:
            await nc.drain()
        except Exception as exc:
            await logger.awarning("identity_events.drain_failed", error=repr(exc))
