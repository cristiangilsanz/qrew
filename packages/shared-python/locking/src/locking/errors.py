# defines the distributed lock's errors
class LockUnavailableError(Exception):
    # stores the key that could not be locked
    def __init__(self, key: str) -> None:
        super().__init__(f"lock unavailable: {key}")
        self.key = key
