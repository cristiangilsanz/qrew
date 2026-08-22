import base64
import binascii
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.audit.core.database import get_db
from com.qode.qrew.v1.audit.core.dependencies import verify_internal_api_key
from com.qode.qrew.v1.audit.models.event import AuditEvent

router = APIRouter(
    prefix="/_internal/events",
    include_in_schema=False,
    dependencies=[Depends(verify_internal_api_key)],
)

_MAX_LIMIT = 100


class _EventItem(BaseModel):
    id: uuid.UUID
    action: str
    entity_type: str | None
    entity_id: str | None
    ip_address: str | None
    device_fingerprint_hash: str | None
    user_agent: str | None
    payload: dict[str, object]
    created_at: datetime


class _EventPage(BaseModel):
    items: list[_EventItem]
    next_cursor: str | None


def _encode(event: AuditEvent) -> str:
    raw = f"{event.created_at.isoformat()}|{event.id}".encode()
    return base64.urlsafe_b64encode(raw).decode()


def _decode(cursor: str) -> tuple[datetime, uuid.UUID]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        stamp, identifier = raw.split("|", 1)
        return datetime.fromisoformat(stamp), uuid.UUID(identifier)
    except (ValueError, binascii.Error) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed cursor"
        ) from exc


@router.get("", response_model=_EventPage)
async def list_events(
    actor_id: uuid.UUID,
    action: str | None = Query(default=None, max_length=64),
    since: datetime | None = None,
    cursor: str | None = None,
    limit: int = Query(default=50, ge=1, le=_MAX_LIMIT),
    db: AsyncSession = Depends(get_db),
) -> _EventPage:
    """Returns a page of the audit trail of one actor, newest first."""
    stmt = select(AuditEvent).where(AuditEvent.actor_id == actor_id)
    if action is not None:
        stmt = stmt.where(AuditEvent.action == action)
    if since is not None:
        stmt = stmt.where(AuditEvent.created_at >= since)
    if cursor is not None:
        created_at, identifier = _decode(cursor)
        stmt = stmt.where(
            or_(
                AuditEvent.created_at < created_at,
                and_(
                    AuditEvent.created_at == created_at,
                    AuditEvent.id < identifier,
                ),
            )
        )
    stmt = stmt.order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc()).limit(limit + 1)
    rows = list((await db.execute(stmt)).scalars().all())
    has_more = len(rows) > limit
    page = rows[:limit]
    return _EventPage(
        items=[
            _EventItem(
                id=row.id,
                action=row.action,
                entity_type=row.entity_type,
                entity_id=row.entity_id,
                ip_address=row.ip_address,
                device_fingerprint_hash=row.device_fingerprint_hash,
                user_agent=row.user_agent,
                payload=row.payload,
                created_at=row.created_at,
            )
            for row in page
        ],
        next_cursor=_encode(page[-1]) if has_more and page else None,
    )
