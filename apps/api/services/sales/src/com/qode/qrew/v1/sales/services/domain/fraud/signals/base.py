from dataclasses import dataclass


@dataclass(frozen=True)
class SignalResult:
    name: str
    score: int
    reason: str
