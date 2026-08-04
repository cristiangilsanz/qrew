from com.qode.qrew.v1.identity.services.application.storage.errors import (
    ObjectNotFoundError,
    SignatureExpiredError,
    SignatureInvalidError,
)
from com.qode.qrew.v1.identity.services.application.storage.security.keys import is_valid_key
from com.qode.qrew.v1.identity.services.application.storage.providers.filesystem import (
    LocalFilesystemBackend,
)
from com.qode.qrew.v1.identity.services.application.storage.uploader import (
    StorageService,
    constraint_for,
)
from com.qode.qrew.v1.identity.core.config import settings

storage = StorageService(
    LocalFilesystemBackend(
        root=settings.storage_root,
        signing_secret=settings.storage_signing_key,
        url_prefix=f"{settings.storage_base_url.rstrip('/')}/v1/uploads/local/",
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
