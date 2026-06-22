class StorageError(Exception):
    """Base error for the storage layer."""


class SignatureInvalidError(StorageError):
    """Raised when a signed URL signature does not validate."""


class SignatureExpiredError(StorageError):
    """Raised when a signed URL has passed its expiry time."""


class ObjectNotFoundError(StorageError):
    """Raised when a storage object does not exist."""
