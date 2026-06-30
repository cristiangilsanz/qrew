from fastapi import APIRouter, Response, status

from com.qode.qrew.v1.gateway.hub.hub import get_hub

router = APIRouter(tags=["probes"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def ready(response: Response) -> dict[str, str]:
    """Reports unavailable until the hub is fully started."""
    try:
        get_hub()
    except RuntimeError:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unavailable"}
    return {"status": "ready"}
