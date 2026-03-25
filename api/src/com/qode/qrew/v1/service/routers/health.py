from fastapi import APIRouter
from pydantic import BaseModel

from com.qode.qrew.v1.service.settings import settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    version: str


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", version=settings.version)
