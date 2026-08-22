import uuid

import httpx
import structlog

from com.qode.qrew.v1.catalog.core.config import settings

logger = structlog.get_logger(__name__)

_TIMEOUT_SECONDS = 5.0
_NOT_FOUND = 404


class IdentityUnavailableError(Exception):
    """Raised when the identity service cannot answer a directory lookup."""


async def resolve_user_id(email: str) -> uuid.UUID | None:
    """Asks identity for the holder of an email address, since catalog does not store it."""
    url = f"{settings.identity_url}/v1/_internal/users/lookup"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            response = await client.post(
                url,
                headers={"X-Internal-Key": settings.internal_api_key},
                json={"email": email},
            )
    except httpx.HTTPError as exc:
        await logger.awarning("identity_lookup_failed", error=str(exc))
        raise IdentityUnavailableError from exc

    if response.status_code == _NOT_FOUND:
        return None
    if response.is_success:
        return uuid.UUID(str(response.json()["user_id"]))

    await logger.awarning("identity_lookup_rejected", status_code=response.status_code)
    raise IdentityUnavailableError
