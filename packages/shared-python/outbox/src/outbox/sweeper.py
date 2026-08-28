# defines the interface an outbox sweeper implements and its generic runner
from typing import Protocol, runtime_checkable


@runtime_checkable
class OutboxSweeper(Protocol):
    # drains a batch of a service's outbox
    async def sweep(self, batch_size: int = 50) -> int: ...


# drains a batch of the outbox through a sweeper
async def sweep_pending(sweeper: OutboxSweeper, batch_size: int = 50) -> int:
    return await sweeper.sweep(batch_size=batch_size)
