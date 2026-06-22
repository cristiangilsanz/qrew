class IdempotencyError(Exception):
    """Base error for the idempotency layer."""


class IdempotencyKeyRequiredError(IdempotencyError):
    """Raised when a protected route receives no idempotency key."""


class IdempotencyKeyConflictError(IdempotencyError):
    """Raised when the same key is reused with a different request fingerprint."""


class IdempotencyInFlightError(IdempotencyError):
    """Raised when another caller is still processing the same idempotency key."""

    def __init__(self, retry_after_seconds: int = 5) -> None:
        super().__init__("request is already being processed")
        self.retry_after_seconds = retry_after_seconds
