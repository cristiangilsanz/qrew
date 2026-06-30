import time
import uuid
from collections.abc import Awaitable, Callable

import structlog
from fastapi import Request

from ratelimit.errors import RateLimitedError
from com.qode.qrew.v1.identity.models.audit import AuditAction
from com.qode.qrew.v1.identity.services.application.audit import AuditService
from com.qode.qrew.v1.identity.core.config import settings

logger = structlog.get_logger(__name__)

_last_record: dict[str, float] = {}


def _debounced(scope_key: str) -> bool:
    """Return whether enough time has passed since the last audit for this scope."""
    window = settings.ratelimit_audit_debounce_seconds
    if window <= 0:
        return True
    now = time.monotonic()
    previous = _last_record.get(scope_key, 0.0)
    if now - previous < window:
        return False
    _last_record[scope_key] = now
    return True


def make_audit_rejection_handler(
    audit: AuditService,
) -> Callable[[Request, RateLimitedError], Awaitable[None]]:
    """Build a rejection handler that records audit events with debouncing."""

    async def handler(request: Request, exc: RateLimitedError) -> None:
        if not _debounced(exc.scope):
            return
        actor_raw = getattr(request.state, "current_user_id", None)
        actor_id: uuid.UUID | None = None
        if actor_raw is not None:
            try:
                actor_id = uuid.UUID(str(actor_raw))
            except ValueError:
                actor_id = None
        try:
            await audit.record(
                action=AuditAction.RATE_LIMIT_HIT,
                actor_id=actor_id,
                ip_address=request.client.host if request.client else None,
                payload={
                    "scope": exc.scope,
                    "limit": exc.limit,
                    "window_seconds": exc.window_seconds,
                    "retry_after_seconds": exc.retry_after_seconds,
                    "path": request.url.path,
                    "method": request.method,
                },
            )
        except Exception as _err:
            await logger.awarning("ratelimit_audit_write_failed", error=repr(_err))

    return handler
