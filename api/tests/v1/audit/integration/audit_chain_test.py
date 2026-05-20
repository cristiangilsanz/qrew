"""Integration tests for the append-only audit log and Merkle hash chain.

Requires a running PostgreSQL with the migration applied.
"""

import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.service.models.audit import AuditAction, AuditEvent
from com.qode.qrew.v1.service.services.audit import AuditService

pytestmark = pytest.mark.integration


# ── record ────────────────────────────────────────────────────────────────────


async def test_record_persists_event(db_session: AsyncSession) -> None:
    audit = AuditService()
    await audit.record(action=AuditAction.REGISTER, payload={"test": True})

    result = await db_session.execute(
        select(AuditEvent).where(AuditEvent.action == AuditAction.REGISTER)
    )
    events = list(result.scalars().all())
    assert len(events) == 1
    assert events[0].hash != b""
    assert len(events[0].hash) == 32


async def test_genesis_event_has_no_prev_hash(db_session: AsyncSession) -> None:
    audit = AuditService()
    await audit.ensure_genesis()

    result = await db_session.execute(
        select(AuditEvent).where(AuditEvent.action == AuditAction.GENESIS)
    )
    genesis = result.scalar_one()
    assert genesis.prev_hash is None


async def test_second_event_prev_hash_equals_genesis_hash(
    db_session: AsyncSession,
) -> None:
    audit = AuditService()
    await audit.ensure_genesis()
    await audit.record(action=AuditAction.REGISTER)

    result = await db_session.execute(
        select(AuditEvent).order_by(AuditEvent.created_at.asc(), AuditEvent.id.asc())
    )
    events = list(result.scalars().all())
    assert len(events) == 2
    genesis, second = events
    assert second.prev_hash == genesis.hash


async def test_ensure_genesis_is_idempotent(db_session: AsyncSession) -> None:
    audit = AuditService()
    await audit.ensure_genesis()
    await audit.ensure_genesis()

    result = await db_session.execute(
        select(AuditEvent).where(AuditEvent.action == AuditAction.GENESIS)
    )
    assert len(list(result.scalars().all())) == 1


# ── verify_chain ──────────────────────────────────────────────────────────────


async def test_verify_chain_passes_for_untampered_chain() -> None:
    audit = AuditService()
    await audit.ensure_genesis()
    await audit.record(action=AuditAction.REGISTER)
    await audit.record(action=AuditAction.VERIFY_EMAIL)
    await audit.record(action=AuditAction.LOGIN)

    result = await audit.verify_chain()
    assert result.valid is True
    assert result.event_count == 4
    assert result.tampered_ids == []


async def test_verify_chain_detects_tampered_payload(db_session: AsyncSession) -> None:
    audit = AuditService()
    await audit.ensure_genesis()
    await audit.record(action=AuditAction.REGISTER, payload={"email": "a@b.com"})
    await audit.record(action=AuditAction.LOGIN)

    # Mutate the register event's payload directly in DB — bypasses app layer
    await db_session.execute(
        text("UPDATE audit_events SET payload = :p::jsonb WHERE action = :action"),
        {"action": AuditAction.REGISTER, "p": '{"email":"hacked@evil.com"}'},
    )
    await db_session.commit()

    result = await audit.verify_chain()
    assert result.valid is False
    assert len(result.tampered_ids) == 1


async def test_verify_chain_detects_tampered_action(db_session: AsyncSession) -> None:
    audit = AuditService()
    await audit.ensure_genesis()
    actor = uuid.uuid4()
    await audit.record(action=AuditAction.LOGIN, actor_id=actor)

    await db_session.execute(
        text("UPDATE audit_events SET action = 'login_failed' WHERE action = 'login'")
    )
    await db_session.commit()

    result = await audit.verify_chain()
    assert result.valid is False


async def test_append_only_trigger_blocks_update(db_session: AsyncSession) -> None:
    """The DB trigger must reject any UPDATE on audit_events."""
    audit = AuditService()
    await audit.ensure_genesis()

    with pytest.raises(Exception, match="append-only"):
        await db_session.execute(
            text("UPDATE audit_events SET action = 'tampered' WHERE action = 'genesis'")
        )


async def test_append_only_trigger_blocks_delete(db_session: AsyncSession) -> None:
    """The DB trigger must reject any DELETE on audit_events."""
    audit = AuditService()
    await audit.ensure_genesis()

    with pytest.raises(Exception, match="append-only"):
        await db_session.execute(text("DELETE FROM audit_events"))
