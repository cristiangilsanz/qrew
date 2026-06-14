from dataclasses import dataclass

import structlog

from com.qode.qrew.v1.identity.core.infra.database import AsyncSessionLocal
from com.qode.qrew.v1.identity.repositories.audit.audit import (
    AuditRepository,
    compute_hash,
    event_to_hashable,
)

logger = structlog.get_logger(__name__)


@dataclass
class ChainVerificationResult:
    valid: bool
    event_count: int
    tampered_ids: list[str]


class AuditChainVerifier:
    """Verify the integrity of the append-only audit hash chain."""

    async def verify(self) -> ChainVerificationResult:
        """Recompute every event hash and report tampered rows."""
        async with AsyncSessionLocal() as session:
            repo = AuditRepository(session)
            events = await repo.get_all_ordered()

        prev_hash: bytes | None = None
        tampered: list[str] = []
        for event in events:
            expected = compute_hash(prev_hash, event_to_hashable(event))
            if event.hash != expected:
                tampered.append(str(event.id))
            prev_hash = event.hash

        return ChainVerificationResult(
            valid=len(tampered) == 0,
            event_count=len(events),
            tampered_ids=tampered,
        )
