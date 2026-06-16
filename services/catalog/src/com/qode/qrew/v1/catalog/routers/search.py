from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.catalog.routers import Page, clamp_limit
from com.qode.qrew.v1.catalog.core.database import get_db
from com.qode.qrew.v1.catalog.core.dependencies import limiter
from com.qode.qrew.v1.catalog.schemas.search import EventSearchResult
from com.qode.qrew.v1.catalog.core.config import settings
from com.qode.qrew.v1.catalog.services.search import SearchService

router = APIRouter(prefix="/events", tags=["events"])

_search_service = SearchService()


@router.get(
    "",
    response_model=Page[EventSearchResult],
    status_code=status.HTTP_200_OK,
    summary="Public catalog list of events with cursor pagination and search",
)
@router.get(
    "/search",
    response_model=Page[EventSearchResult],
    status_code=status.HTTP_200_OK,
    summary="Search published events by text and filters",
    include_in_schema=False,
)
@limiter.limit("120/minute")  # type: ignore[misc]
async def search_events(
    request: Request,
    q: str | None = Query(default=None, max_length=256),
    city: str | None = Query(default=None, max_length=128),
    category: str | None = Query(default=None, max_length=64),
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = Query(default=None, alias="to"),
    cursor: str | None = None,
    limit: int = Query(default=settings.search_default_limit, ge=1),
    db: AsyncSession = Depends(get_db),
) -> Page[EventSearchResult]:
    del request
    page_limit = clamp_limit(limit, default=settings.search_default_limit)
    page_limit = min(page_limit, settings.search_max_limit)

    return await _search_service.search_events(
        db,
        q=q,
        city=city,
        category=category,
        from_=from_,
        to=to,
        cursor=cursor,
        limit=page_limit,
    )
