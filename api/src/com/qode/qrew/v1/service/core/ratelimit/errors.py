from dataclasses import dataclass


@dataclass(frozen=True)
class RateLimitedError(Exception):
    """Raised by the limiter when at least one scope is over its budget."""

    scope: str
    limit: int
    window_seconds: int
    retry_after_seconds: int

    def __str__(self) -> str:
        return (
            f"rate limit exceeded for {self.scope} "
            f"(limit={self.limit}, window={self.window_seconds}s)"
        )
