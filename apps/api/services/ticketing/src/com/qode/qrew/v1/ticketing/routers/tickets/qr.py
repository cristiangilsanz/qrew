import asyncio
import json
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.ticketing.services.application.audit import AuditService
from com.qode.qrew.v1.ticketing.core.principals import AuthenticatedUser, get_current_user
from com.qode.qrew.v1.ticketing.core.database import get_db
from com.qode.qrew.v1.ticketing.core.dependencies import get_audit_service, limiter
from com.qode.qrew.v1.ticketing.schemas.tickets.qr import QrIssueRequest, QrResponse
from com.qode.qrew.v1.ticketing.services.domain.gate import (
    DenialReason,
    GateInputs,
    evaluate_gate,
    load_inputs,
)
from com.qode.qrew.v1.ticketing.services.application.tickets.mint import mint_qr, record_denial
from com.qode.qrew.v1.ticketing.core.config import settings

router = APIRouter(prefix="/tickets", tags=["ticket-qr"])

_REASON_TO_STATUS: dict[DenialReason, int] = {
    DenialReason.not_found: status.HTTP_404_NOT_FOUND,
    DenialReason.not_owner: status.HTTP_404_NOT_FOUND,
    DenialReason.state: status.HTTP_409_CONFLICT,
    DenialReason.reassertion: status.HTTP_403_FORBIDDEN,
    DenialReason.attestation: status.HTTP_403_FORBIDDEN,
    DenialReason.geofence: status.HTTP_403_FORBIDDEN,
}


def _denied_exception(reason: DenialReason) -> HTTPException:
    return HTTPException(
        status_code=_REASON_TO_STATUS[reason],
        detail={"message": "QR mint denied", "field": reason.value},
    )


async def _resolve_or_deny(
    db: AsyncSession,
    *,
    ticket_id: uuid.UUID,
    current_user: AuthenticatedUser,
    latitude: float,
    longitude: float,
    now: datetime,
    audit: AuditService,
) -> GateInputs:
    device_id = current_user.device_id
    if device_id is None:
        await record_denial(
            audit=audit,
            user_id=current_user.id,
            ticket_id=ticket_id,
            reason=DenialReason.attestation.value,
            device_id=None,
        )
        raise _denied_exception(DenialReason.attestation)
    resolved = await load_inputs(
        db, ticket_id=ticket_id, user_id=current_user.id, device_id=device_id
    )
    if isinstance(resolved, DenialReason):
        await record_denial(
            audit=audit,
            user_id=current_user.id,
            ticket_id=ticket_id,
            reason=resolved.value,
            device_id=device_id,
        )
        raise _denied_exception(resolved)
    reason = evaluate_gate(
        resolved,
        last_asserted_at=current_user.last_asserted_at,  # type: ignore[arg-type]
        latitude=latitude,
        longitude=longitude,
        now=now,
    )
    if reason is not None:
        await record_denial(
            audit=audit,
            user_id=current_user.id,
            ticket_id=ticket_id,
            reason=reason.value,
            device_id=device_id,
        )
        raise _denied_exception(reason)
    return resolved


@router.get(
    "/{ticket_id}/qr",
    response_model=QrResponse,
    status_code=status.HTTP_200_OK,
    summary="Mint a fresh rotating QR for a ticket",
)
@limiter.limit("30/minute")  # type: ignore[misc]
async def issue_qr(
    request: Request,
    ticket_id: uuid.UUID,
    latitude: float = Query(..., ge=-90.0, le=90.0),
    longitude: float = Query(..., ge=-180.0, le=180.0),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    audit: AuditService = Depends(get_audit_service),
) -> QrResponse:
    del request
    now = datetime.now(UTC)
    device_id = current_user.device_id
    inputs = await _resolve_or_deny(
        db,
        ticket_id=ticket_id,
        current_user=current_user,
        latitude=latitude,
        longitude=longitude,
        now=now,
        audit=audit,
    )
    minted = await mint_qr(
        inputs=inputs,
        user_id=current_user.id,
        device_id=device_id,  # type: ignore[arg-type]
        audit=audit,
        now=now,
    )
    return QrResponse(
        ticket_id=inputs.ticket.id,
        jwt=minted.jwt,
        jti=minted.jti,
        issued_at=minted.issued_at,
        expires_at=minted.expires_at,
        rotates_at=minted.expires_at,
    )


@router.post(
    "/{ticket_id}/qr/stream",
    status_code=status.HTTP_200_OK,
    summary="Server-sent stream of rotating QRs while the gate is open",
)
@limiter.limit("10/minute")  # type: ignore[misc]
async def stream_qr(
    request: Request,
    ticket_id: uuid.UUID,
    body: QrIssueRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    audit: AuditService = Depends(get_audit_service),
) -> StreamingResponse:
    del request
    latitude = float(body.latitude)
    longitude = float(body.longitude)
    device_id = current_user.device_id

    async def _events() -> AsyncGenerator[bytes, None]:
        deadline = datetime.now(UTC).timestamp() + settings.ticket_qr_stream_max_seconds
        while datetime.now(UTC).timestamp() < deadline:
            now = datetime.now(UTC)
            try:
                inputs = await _resolve_or_deny(
                    db,
                    ticket_id=ticket_id,
                    current_user=current_user,
                    latitude=latitude,
                    longitude=longitude,
                    now=now,
                    audit=audit,
                )
            except HTTPException as exc:
                payload = json.dumps({"type": "denied", "detail": exc.detail})
                yield f"event: denied\ndata: {payload}\n\n".encode()
                return
            minted = await mint_qr(
                inputs=inputs,
                user_id=current_user.id,
                device_id=device_id,  # type: ignore[arg-type]
                audit=audit,
                now=now,
            )
            payload = json.dumps(
                {
                    "ticket_id": str(inputs.ticket.id),
                    "jwt": minted.jwt,
                    "jti": minted.jti,
                    "issued_at": minted.issued_at.isoformat(),
                    "expires_at": minted.expires_at.isoformat(),
                }
            )
            yield f"event: qr\ndata: {payload}\n\n".encode()
            await asyncio.sleep(settings.ticket_qr_ttl_seconds)

    return StreamingResponse(_events(), media_type="text/event-stream")
