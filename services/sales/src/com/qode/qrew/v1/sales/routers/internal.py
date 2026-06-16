"""Internal API routes consumed only by sibling services."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.sales.core.database import get_db
from com.qode.qrew.v1.sales.core.config import settings
from com.qode.qrew.v1.sales.services.payment_context import (
    PaymentContext,
    PaymentContextError,
    get_payment_context,
)

router = APIRouter(prefix="/_internal", include_in_schema=False)

_ERROR_STATUS = {
    "not_found": status.HTTP_404_NOT_FOUND,
    "not_reserved": status.HTTP_400_BAD_REQUEST,
    "expired": status.HTTP_410_GONE,
}


def _require_internal_key(request: Request) -> None:
    key = request.headers.get("X-Internal-Key", "")
    if not key or key != settings.internal_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


class _PaymentContextRequest(BaseModel):
    user_id: uuid.UUID


class _PaymentContextResponse(BaseModel):
    amount_cents: int
    currency: str


def _to_response(ctx: PaymentContext) -> _PaymentContextResponse:
    return _PaymentContextResponse(amount_cents=ctx.amount_cents, currency=ctx.currency)


@router.post(
    "/reservations/{reservation_id}/payment-context",
    response_model=_PaymentContextResponse,
)
async def get_reservation_payment_context(
    reservation_id: uuid.UUID,
    body: _PaymentContextRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> _PaymentContextResponse:
    """Returns the billable amount and currency for a reservation."""
    _require_internal_key(request)
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
