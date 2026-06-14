from com.qode.qrew.v1.identity.services.storage.errors import (
    ObjectNotFoundError,
    SignatureExpiredError,
    SignatureInvalidError,
)
from com.qode.qrew.v1.identity.services.storage.keys import is_valid_key
from com.qode.qrew.v1.identity.services.storage.local import LocalFilesystemBackend
from com.qode.qrew.v1.identity.services.storage.service import StorageService, constraint_for
from com.qode.qrew.v1.identity.settings import settings

storage = StorageService(
    LocalFilesystemBackend(
        root=settings.storage_root,
        signing_secret=settings.storage_signing_key,
    )
)

__all__ = [
    "ObjectNotFoundError",
    "SignatureExpiredError",
    "SignatureInvalidError",
    "constraint_for",
    "is_valid_key",
    "storage",
]
