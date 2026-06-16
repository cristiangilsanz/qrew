from fastapi import APIRouter

router = APIRouter(tags=["probes"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
