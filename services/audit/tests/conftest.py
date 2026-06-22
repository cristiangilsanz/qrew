import uuid
from datetime import UTC, datetime

import pytest

from com.qode.qrew.v1.audit.models.event import AuditAction, AuditEvent
from com.qode.qrew.v1.audit.repositories.audit import build_event


@pytest.fixture
def make_chain():
    def _factory(n: int, *, action: str = AuditAction.LOGIN) -> list[AuditEvent]:
        events: list[AuditEvent] = []
        prev_hash: bytes | None = None
        for _ in range(n):
            event = build_event(
                action=action,
                actor_id=uuid.uuid4(),
                entity_type="user",
                entity_id=str(uuid.uuid4()),
                ip_address=None,
                device_fingerprint_hash=None,
                user_agent=None,
                payload={},
                created_at=datetime(2024, 1, 1, tzinfo=UTC),
                prev_hash=prev_hash,
            )
            prev_hash = event.hash
            events.append(event)
        return events

    return _factory
