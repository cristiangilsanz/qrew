import uuid
from dataclasses import dataclass

import httpx
import structlog

from com.qode.qrew.v1.entry.core.config import settings

logger = structlog.get_logger(__name__)

_TIMEOUT_SECONDS = 5.0


class CatalogUnavailableError(Exception):
    """Raised when the catalog service cannot answer a membership question."""


@dataclass(frozen=True)
class EventMembership:
    event_exists: bool
    is_member: bool
    venue_id: uuid.UUID | None


async def fetch_event_membership(
    event_id: uuid.UUID, user_id: uuid.UUID
) -> EventMembership:
    """Asks catalog whether a user belongs to the organisation that owns an event."""
    url = f"{settings.catalog_url}/v1/_internal/events/{event_id}/members/{user_id}"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            response = await client.get(
                url, headers={"X-Internal-Key": settings.internal_api_key}
            )
    except httpx.HTTPError as exc:
        await logger.awarning("catalog_membership_failed", error=str(exc))
        raise CatalogUnavailableError from exc

    if not response.is_success:
        await logger.awarning(
            "catalog_membership_rejected", status_code=response.status_code
        )
        raise CatalogUnavailableError

    body = response.json()
    venue_id = body.get("venue_id")
    return EventMembership(
        event_exists=bool(body["event_exists"]),
        is_member=bool(body["is_member"]),
        venue_id=uuid.UUID(str(venue_id)) if venue_id else None,
    )
