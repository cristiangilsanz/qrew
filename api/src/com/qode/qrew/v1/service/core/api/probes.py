from typing import Any

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_200_OK, HTTP_503_SERVICE_UNAVAILABLE

from com.qode.qrew.v1.service.core.infra.database import get_db
from com.qode.qrew.v1.service.core.infra.redis import get_redis

router = APIRouter(tags=["probes"], include_in_schema=False)


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    """Confirm that the service process is up."""
    return {"status": "ok"}


@router.get("/readyz")
async def readyz(
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),  # type: ignore[type-arg]
) -> JSONResponse:
    """Confirm that the service can reach its critical dependencies."""
    deps: dict[str, str] = {}
    failures: list[str] = []

    try:
        await db.execute(text("SELECT 1"))
        deps["db"] = "ok"
    except Exception:
        deps["db"] = "fail"
        failures.append("db")

    try:
        await redis.ping()  # type: ignore[misc]
        deps["redis"] = "ok"
    except Exception:
        deps["redis"] = "fail"
        failures.append("redis")

    body: dict[str, Any] = {"deps": deps, "failures": failures}
    status_code = HTTP_503_SERVICE_UNAVAILABLE if failures else HTTP_200_OK
    return JSONResponse(status_code=status_code, content=body)
