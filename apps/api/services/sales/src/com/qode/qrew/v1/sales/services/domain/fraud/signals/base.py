# defines the result a fraud signal returns
from dataclasses import dataclass


@dataclass(frozen=True)
class SignalResult:
    name: str
    score: int
    reason: str
