from typing import Protocol, runtime_checkable


@runtime_checkable
class OutboxSweeper(Protocol):
    """Protocol for transactional outbox sweeper implementations."""

    async def sweep(self, batch_size: int = 50) -> int:
        """Publish pending outbox records. Returns the number of records processed."""
        ...


async def sweep_pending(sweeper: OutboxSweeper, batch_size: int = 50) -> int:
    """Convenience wrapper that calls the sweeper and returns the count."""
    return await sweeper.sweep(batch_size=batch_size)
