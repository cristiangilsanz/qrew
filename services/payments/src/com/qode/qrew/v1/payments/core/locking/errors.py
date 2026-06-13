class LockUnavailableError(Exception):
    def __init__(self, key: str) -> None:
        super().__init__(f"Could not acquire lock: {key}")
        self.key = key
