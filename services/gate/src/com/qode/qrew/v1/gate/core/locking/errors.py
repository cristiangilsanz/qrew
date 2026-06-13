class LockUnavailableError(Exception):
    def __init__(self, key: str) -> None:
        super().__init__(f"lock unavailable: {key}")
        self.key = key
