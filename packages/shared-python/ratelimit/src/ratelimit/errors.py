# defines the shared rate limiter's rejection error
from dataclasses import dataclass


@dataclass(frozen=True)
class RateLimitedError(Exception):
    scope: str
    limit: int
    window_seconds: int
    retry_after_seconds: int

    # renders a human readable description of the rejection
    def __str__(self) -> str:
        return (
            f"rate limit exceeded for {self.scope} "
            f"(limit={self.limit}, window={self.window_seconds}s)"
        )
