class IdempotencyError(Exception):
    pass


class IdempotencyKeyRequiredError(IdempotencyError):
    pass


class IdempotencyKeyConflictError(IdempotencyError):
    pass


class IdempotencyInFlightError(IdempotencyError):
    def __init__(self, retry_after_seconds: int = 5) -> None:
        super().__init__("request is already being processed")
        self.retry_after_seconds = retry_after_seconds
