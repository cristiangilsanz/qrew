class LockUnavailableError(Exception):
    """Raised when a distributed lock cannot be acquired within the retry budget."""

    def __init__(self, key: str) -> None:
        super().__init__(f"lock unavailable: {key}")
        self.key = key
