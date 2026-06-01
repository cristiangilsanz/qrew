from com.qode.qrew.v1.service.core.storage.backend import StorageBackend
from com.qode.qrew.v1.service.core.storage.errors import (
    ObjectNotFoundError,
    SignatureExpiredError,
    SignatureInvalidError,
    StorageError,
)
from com.qode.qrew.v1.service.core.storage.keys import (
    ObjectKey,
    build_key,
    is_known_kind,
    is_valid_key,
    kind_for,
)
from com.qode.qrew.v1.service.core.storage.local import LocalFilesystemBackend
from com.qode.qrew.v1.service.core.storage.service import (
    StorageService,
    UploadConstraint,
    constraint_for,
)
from com.qode.qrew.v1.service.core.storage.signing import SignedUrl
from com.qode.qrew.v1.service.settings import settings


def _build_default_service() -> StorageService:
    backend = LocalFilesystemBackend(
        root=settings.storage_root,
        signing_secret=settings.storage_signing_key,
    )
    return StorageService(backend)


storage: StorageService = _build_default_service()


__all__ = [
    "LocalFilesystemBackend",
    "ObjectKey",
    "ObjectNotFoundError",
    "SignatureExpiredError",
    "SignatureInvalidError",
    "SignedUrl",
    "StorageBackend",
    "StorageError",
    "StorageService",
    "UploadConstraint",
    "build_key",
    "constraint_for",
    "is_known_kind",
    "is_valid_key",
    "kind_for",
    "storage",
]
