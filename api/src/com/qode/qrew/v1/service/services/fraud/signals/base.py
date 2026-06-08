from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from com.qode.qrew.v1.service.services.fraud.context import PurchaseContext


@dataclass(frozen=True)
class SignalResult:
    name: str
    score: int
    reason: str


@runtime_checkable
class Signal(Protocol):
    """Stateless, synchronous-or-async scoring fragment."""

    name: str

    async def evaluate(self, context: PurchaseContext) -> SignalResult: ...
