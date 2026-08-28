# exposes the identity client used by the catalog service
from com.qode.qrew.v1.catalog.services.application.identity.directory import (
    IdentityUnavailableError,
    resolve_user_id,
)

__all__ = ["IdentityUnavailableError", "resolve_user_id"]
