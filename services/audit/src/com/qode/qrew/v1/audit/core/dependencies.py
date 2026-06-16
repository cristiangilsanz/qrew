from fastapi import Header, HTTPException, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from com.qode.qrew.v1.audit.core.config import settings

limiter = Limiter(key_func=get_remote_address, enabled=settings.ratelimit_enabled)


async def verify_internal_api_key(
    x_internal_key: str = Header(alias="X-Internal-Key"),
) -> None:
    if x_internal_key != settings.internal_api_key:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
