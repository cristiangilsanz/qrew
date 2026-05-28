"""Unit tests for the audit chain verifier."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from com.qode.qrew.v1.service.models.audit.audit import AuditAction, AuditEvent
from com.qode.qrew.v1.service.repositories.audit.audit import (
    compute_hash,
    event_to_hashable,
)
from com.qode.qrew.v1.service.services.audit import AuditChainVerifier

_REPO_PATH = "com.qode.qrew.v1.service.services.audit.verifier.AuditRepository"


def _make_event(
    action: str,
    *,
    prev_hash: bytes | None,
    actor_id: uuid.UUID | None = None,
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


def _chain(actions: list[str]) -> list[AuditEvent]:
    events: list[AuditEvent] = []
    prev_hash: bytes | None = None
    for action in actions:
        event = _make_event(action, prev_hash=prev_hash)
        events.append(event)
        prev_hash = event.hash
    return events


@pytest.fixture
def mock_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.get_all_ordered = AsyncMock()
    return repo


async def _run(mock_repo: AsyncMock) -> object:
    with patch(_REPO_PATH) as repo_cls:
        repo_cls.return_value = mock_repo
        return await AuditChainVerifier().verify()


async def test_empty_chain_is_valid(mock_repo: AsyncMock) -> None:
    mock_repo.get_all_ordered.return_value = []
    result = await _run(mock_repo)
    assert result.valid is True  # type: ignore[attr-defined]
    assert result.event_count == 0  # type: ignore[attr-defined]
    assert result.tampered_ids == []  # type: ignore[attr-defined]


async def test_intact_chain_is_valid(mock_repo: AsyncMock) -> None:
    events = _chain([AuditAction.GENESIS, AuditAction.REGISTER, AuditAction.LOGIN])
    mock_repo.get_all_ordered.return_value = events
    result = await _run(mock_repo)
    assert result.valid is True  # type: ignore[attr-defined]
    assert result.event_count == 3  # type: ignore[attr-defined]
    assert result.tampered_ids == []  # type: ignore[attr-defined]


async def test_tampered_payload_is_detected(mock_repo: AsyncMock) -> None:
    events = _chain([AuditAction.GENESIS, AuditAction.REGISTER])
    events[1].action = AuditAction.LOGOUT
    mock_repo.get_all_ordered.return_value = events
    result = await _run(mock_repo)
    assert result.valid is False  # type: ignore[attr-defined]
    assert str(events[1].id) in result.tampered_ids  # type: ignore[attr-defined]


async def test_tampered_genesis_does_not_cascade(mock_repo: AsyncMock) -> None:
    events = _chain([AuditAction.GENESIS, AuditAction.REGISTER, AuditAction.LOGIN])
    events[0].action = "tampered"
    mock_repo.get_all_ordered.return_value = events
    result = await _run(mock_repo)
    assert result.valid is False  # type: ignore[attr-defined]
    assert str(events[0].id) in result.tampered_ids  # type: ignore[attr-defined]
    assert str(events[1].id) not in result.tampered_ids  # type: ignore[attr-defined]
    assert str(events[2].id) not in result.tampered_ids  # type: ignore[attr-defined]


async def test_event_count_reflects_full_chain_length(mock_repo: AsyncMock) -> None:
    events = _chain(
        [
            AuditAction.GENESIS,
            AuditAction.REGISTER,
            AuditAction.LOGIN,
            AuditAction.LOGOUT,
        ]
    )
    mock_repo.get_all_ordered.return_value = events
    result = await _run(mock_repo)
    assert result.event_count == 4  # type: ignore[attr-defined]
