# exposes the health probe endpoint for the audit service
from fastapi import APIRouter

router = APIRouter(tags=["probes"])


# reports that the service is running
@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
