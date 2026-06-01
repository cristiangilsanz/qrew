class IdempotencyError(Exception):
    """Base error raised by the idempotency layer."""


class IdempotencyKeyRequiredError(IdempotencyError):
    """Raised when a marked route requires a key and none was supplied."""


class IdempotencyKeyConflictError(IdempotencyError):
    """Raised when the same key is reused for a different request."""


class IdempotencyInFlightError(IdempotencyError):
    """Raised when another caller is still processing the same key."""

    def __init__(self, retry_after_seconds: int = 5) -> None:
        super().__init__("request is already being processed")
        self.retry_after_seconds = retry_after_seconds
