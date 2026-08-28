# fetches a user's audit trail from the audit service
import uuid
from dataclasses import dataclass
from datetime import datetime

import httpx
import structlog

from com.qode.qrew.v1.identity.core.config import settings

logger = structlog.get_logger(__name__)

_TIMEOUT_SECONDS = 5.0


class AuditUnavailableError(Exception):
    pass


@dataclass(frozen=True)
class AuditTrailEntry:
    id: uuid.UUID
    action: str
    entity_type: str | None
    ip_address: str | None
    device_fingerprint_hash: str | None
    payload: dict[str, object]
    created_at: datetime


@dataclass(frozen=True)
class AuditTrailPage:
    items: list[AuditTrailEntry]
    next_cursor: str | None


# fetches a page of a user's audit trail from the audit service
async def fetch_trail(
    actor_id: uuid.UUID,
    *,
    action: str | None = None,
    since: datetime | None = None,
    cursor: str | None = None,
    limit: int = 50,
) -> AuditTrailPage:
    params: dict[str, str] = {"actor_id": str(actor_id), "limit": str(limit)}
    if action is not None:
        params["action"] = action
    if since is not None:
        params["since"] = since.isoformat()
    if cursor is not None:
        params["cursor"] = cursor

    url = f"{settings.audit_url}/v1/_internal/events"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            response = await client.get(
                url, params=params, headers={"X-Internal-Key": settings.internal_api_key}
            )
    except httpx.HTTPError as exc:
        await logger.awarning("audit_trail_failed", error=str(exc))
        raise AuditUnavailableError from exc

    if not response.is_success:
        await logger.awarning("audit_trail_rejected", status_code=response.status_code)
        raise AuditUnavailableError

    body = response.json()
    return AuditTrailPage(
        items=[
            AuditTrailEntry(
                id=uuid.UUID(str(item["id"])),
                action=str(item["action"]),
                entity_type=item.get("entity_type"),
                ip_address=item.get("ip_address"),
                device_fingerprint_hash=item.get("device_fingerprint_hash"),
                payload=item.get("payload") or {},
                created_at=datetime.fromisoformat(str(item["created_at"])),
            )
            for item in body["items"]
        ],
        next_cursor=body.get("next_cursor"),
    )
