from fastapi import APIRouter
from pydantic import BaseModel

from com.qode.qrew.v1.service.settings import settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    version: str


@router.get("/health", response_model=HealthResponse, summary="Check service health")
async def health() -> HealthResponse:
    """Return the current service status."""
    return HealthResponse(status="ok", version=settings.version)
