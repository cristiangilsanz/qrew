from db import create_redis_dependency
from fastapi import Header, HTTPException, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from com.qode.qrew.v1.ticketing.core.config import settings
from com.qode.qrew.v1.ticketing.services.application.audit import AuditService

limiter = Limiter(key_func=get_remote_address, enabled=settings.ratelimit_enabled)

get_redis = create_redis_dependency(settings.redis_url)


async def verify_internal_key(
    x_internal_key: str = Header(alias="X-Internal-Key", default=""),
) -> None:
    if not x_internal_key or x_internal_key != settings.internal_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


def get_audit_service() -> AuditService:
    return AuditService()
