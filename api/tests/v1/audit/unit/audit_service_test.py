"""Unit tests for the Merkle hash chain logic in the audit repository."""

import hashlib
import json
import uuid
from datetime import UTC, datetime

from com.qode.qrew.v1.service.models.audit import AuditAction, AuditEvent
from com.qode.qrew.v1.service.repositories.audit import (
    compute_hash,
    event_to_hashable,
)


def _make_event(
    action: str = AuditAction.GENESIS,
    actor_id: uuid.UUID | None = None,
    prev_hash: bytes | None = None,
) -> AuditEvent:
    event = AuditEvent(
        id=uuid.uuid4(),
        actor_id=actor_id,
        action=action,
        entity_type="user",
        entity_id=None,
        ip_address=None,
        device_fingerprint_hash=None,
        user_agent=None,
        payload={},
        created_at=datetime(2026, 5, 20, 12, 0, 0, tzinfo=UTC),
        prev_hash=prev_hash,
        hash=b"",
    )
    event.hash = compute_hash(prev_hash, event_to_hashable(event))
    return event


# ── compute_hash ──────────────────────────────────────────────────────────────


def test_compute_hash_produces_32_bytes() -> None:
    # Given
    data: dict[str, object] = {"key": "value"}

    # When
    result = compute_hash(None, data)

    # Then
    assert len(result) == 32


def test_compute_hash_is_deterministic() -> None:
    # Given
    data: dict[str, object] = {"id": "abc", "action": "register"}

    # When
    h1 = compute_hash(None, data)
    h2 = compute_hash(None, data)

    # Then
    assert h1 == h2


def test_compute_hash_changes_when_data_changes() -> None:
    # Given
    data_a: dict[str, object] = {"action": "register"}
    data_b: dict[str, object] = {"action": "logout"}

    # Then
    assert compute_hash(None, data_a) != compute_hash(None, data_b)


def test_compute_hash_changes_when_prev_hash_changes() -> None:
    # Given
    data: dict[str, object] = {"action": "login"}
    prev_a = b"\x00" * 32
    prev_b = b"\xff" * 32

    # Then
    assert compute_hash(prev_a, data) != compute_hash(prev_b, data)


def test_compute_hash_with_none_prev_differs_from_zero_prev() -> None:
    # Given
    data: dict[str, object] = {"action": "login"}

    # Then
    assert compute_hash(None, data) != compute_hash(b"\x00" * 32, data)


def test_compute_hash_matches_manual_sha256() -> None:
    # Given
    data: dict[str, object] = {"id": "x", "action": "genesis"}
    canonical = json.dumps(
        data, sort_keys=True, default=str, separators=(",", ":")
    ).encode()
    expected = hashlib.sha256(canonical).digest()

    # Then
    assert compute_hash(None, data) == expected


# ── event_to_hashable ─────────────────────────────────────────────────────────


def test_event_to_hashable_excludes_hash_fields() -> None:
    # Given
    event = _make_event()

    # When
    hashable = event_to_hashable(event)

    # Then
    assert "hash" not in hashable
    assert "prev_hash" not in hashable


def test_event_to_hashable_includes_required_fields() -> None:
    # Given
    actor = uuid.uuid4()
    event = _make_event(actor_id=actor)

    # When
    hashable = event_to_hashable(event)

    # Then
    assert hashable["id"] == str(event.id)
    assert hashable["actor_id"] == str(actor)
    assert hashable["action"] == AuditAction.GENESIS
    assert "created_at" in hashable


# ── chain integrity ───────────────────────────────────────────────────────────


def test_chain_of_two_events_is_valid() -> None:
    # Given
    genesis = _make_event(action=AuditAction.GENESIS, prev_hash=None)
    second = _make_event(action=AuditAction.REGISTER, prev_hash=genesis.hash)

    # Then
    assert genesis.prev_hash is None
    assert second.prev_hash == genesis.hash

    expected_genesis = compute_hash(None, event_to_hashable(genesis))
    assert genesis.hash == expected_genesis

    expected_second = compute_hash(genesis.hash, event_to_hashable(second))
    assert second.hash == expected_second


def test_mutating_event_breaks_its_hash() -> None:
    # Given
    event = _make_event(action=AuditAction.REGISTER, prev_hash=None)
    original_hash = event.hash

    # When
    event.action = AuditAction.LOGOUT

    # Then
    recomputed = compute_hash(event.prev_hash, event_to_hashable(event))
    assert recomputed != original_hash


def test_mutating_first_event_breaks_second_event_link() -> None:
    # Given
    genesis = _make_event(action=AuditAction.GENESIS, prev_hash=None)
    second = _make_event(action=AuditAction.REGISTER, prev_hash=genesis.hash)

    # When
    genesis.action = "tampered"

    # Then
    recomputed_genesis = compute_hash(None, event_to_hashable(genesis))
    assert second.prev_hash != recomputed_genesis
