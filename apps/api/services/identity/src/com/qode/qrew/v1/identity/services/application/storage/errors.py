# defines the storage service's errors
class StorageError(Exception):
    pass


class SignatureInvalidError(StorageError):
    pass


class SignatureExpiredError(StorageError):
    pass


class ObjectNotFoundError(StorageError):
    pass
