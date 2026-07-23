import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.sales.core.database import get_db
from com.qode.qrew.v1.sales.core.config import settings
from com.qode.qrew.v1.sales.core.dependencies import get_market_service, verify_internal_key
from com.qode.qrew.v1.sales.services.application.billing import (
    PaymentContext,
    PaymentContextError,
    get_payment_context,
)
from com.qode.qrew.v1.sales.services.application.market.service import MarketError, MarketService

router = APIRouter(
    prefix="/billing",
    include_in_schema=False,
    dependencies=[Depends(verify_internal_key)],
)

_ERROR_STATUS = {
    "not_found": status.HTTP_404_NOT_FOUND,
    "not_reserved": status.HTTP_400_BAD_REQUEST,
    "expired": status.HTTP_410_GONE,
}


class _PaymentContextRequest(BaseModel):
    user_id: uuid.UUID


class _PaymentContextResponse(BaseModel):
    amount_cents: int
    currency: str


def _to_response(ctx: PaymentContext) -> _PaymentContextResponse:
    return _PaymentContextResponse(amount_cents=ctx.amount_cents, currency=ctx.currency)


@router.post(
    "/reservations/{reservation_id}/charge",
    response_model=_PaymentContextResponse,
)
async def create_charge(
    reservation_id: uuid.UUID,
    body: _PaymentContextRequest,
    db: AsyncSession = Depends(get_db),
) -> _PaymentContextResponse:
    """Returns the billable amount and currency for a reservation."""
    try:
        ctx = await get_payment_context(
            db,
            reservation_id=reservation_id,
            user_id=body.user_id,
            default_currency=settings.payments_default_currency,
        )
    except PaymentContextError as exc:
        raise HTTPException(
            status_code=_ERROR_STATUS.get(exc.error_code, status.HTTP_400_BAD_REQUEST),
            detail={"error_code": exc.error_code, "message": exc.message},
        ) from exc
    return _to_response(ctx)


@router.post(
    "/market-assignments/{assignment_id}/charge",
    response_model=_PaymentContextResponse,
)
async def create_market_assignment_charge(
    assignment_id: uuid.UUID,
    body: _PaymentContextRequest,
    db: AsyncSession = Depends(get_db),
    service: MarketService = Depends(get_market_service),
) -> _PaymentContextResponse:
    """Returns the billable amount and currency for a market assignment."""
    try:
        ctx = await service.get_payment_context(user_id=body.user_id, assignment_id=assignment_id)
    except MarketError as exc:
        code = (
            status.HTTP_404_NOT_FOUND
            if exc.field in {"assignment_id", "listing_id"}
            else status.HTTP_410_GONE
            if exc.field == "expires_at"
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(
            status_code=code,
            detail={"error_code": exc.field, "message": exc.message},
        ) from exc
    return _PaymentContextResponse(amount_cents=ctx["amount_cents"], currency=ctx["currency"])
