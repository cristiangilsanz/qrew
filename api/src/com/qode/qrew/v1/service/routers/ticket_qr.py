import asyncio
import json
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.service.core.auth.auth import (
    get_current_session,
    get_current_user,
)
from com.qode.qrew.v1.service.core.infra.database import get_db
from com.qode.qrew.v1.service.core.infra.limiter import limiter
from com.qode.qrew.v1.service.models.auth.session import Session
from com.qode.qrew.v1.service.models.auth.user import User
from com.qode.qrew.v1.service.schemas.ticket_qr import QrIssueRequest, QrResponse
from com.qode.qrew.v1.service.services.audit import AuditService
from com.qode.qrew.v1.service.services.ticket_qr import (
    DenialReason,
    GateInputs,
    evaluate_gate,
    load_inputs,
    mint_qr,
    record_denial,
)
from com.qode.qrew.v1.service.settings import settings

router = APIRouter(tags=["ticket-qr"])

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
    user_id: uuid.UUID,
    auth_session: Session,
    latitude: float,
    longitude: float,
    now: datetime,
    audit: AuditService,
) -> GateInputs:
    device_id = auth_session.device_id
    if device_id is None:
        await record_denial(
            audit=audit,
            user_id=user_id,
            ticket_id=ticket_id,
            reason=DenialReason.attestation.value,
            device_id=None,
        )
        raise _denied_exception(DenialReason.attestation)
    resolved = await load_inputs(
        db, ticket_id=ticket_id, user_id=user_id, device_id=device_id
    )
    if isinstance(resolved, DenialReason):
        await record_denial(
            audit=audit,
            user_id=user_id,
            ticket_id=ticket_id,
            reason=resolved.value,
            device_id=device_id,
        )
        raise _denied_exception(resolved)
    reason = evaluate_gate(
        resolved,
        auth_session=auth_session,
        latitude=latitude,
        longitude=longitude,
        now=now,
    )
    if reason is not None:
        await record_denial(
            audit=audit,
            user_id=user_id,
            ticket_id=ticket_id,
            reason=reason.value,
            device_id=device_id,
        )
        raise _denied_exception(reason)
    return resolved


@router.get(
    "/tickets/{ticket_id}/qr",
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
    current_user: User = Depends(get_current_user),
    auth_session: Session = Depends(get_current_session),
    db: AsyncSession = Depends(get_db),
) -> QrResponse:
    """Single-shot QR mint. Client polls just before `rotates_at`."""
    del request
    audit = AuditService()
    now = datetime.now(UTC)
    inputs = await _resolve_or_deny(
        db,
        ticket_id=ticket_id,
        user_id=current_user.id,
        auth_session=auth_session,
        latitude=latitude,
        longitude=longitude,
        now=now,
        audit=audit,
    )
    minted = await mint_qr(
        inputs=inputs,
        user_id=current_user.id,
        device_id=inputs.device.id,
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
    "/tickets/{ticket_id}/qr/stream",
    status_code=status.HTTP_200_OK,
    summary="Server-sent stream of rotating QRs while the gate is open",
)
@limiter.limit("10/minute")  # type: ignore[misc]
async def stream_qr(
    request: Request,
    ticket_id: uuid.UUID,
    body: QrIssueRequest,
    current_user: User = Depends(get_current_user),
    auth_session: Session = Depends(get_current_session),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Stream a fresh JWT every TTL seconds; close when any gate fails."""
    del request
    audit = AuditService()
    latitude = float(body.latitude)
    longitude = float(body.longitude)
    user_id = current_user.id

    async def _events() -> AsyncGenerator[bytes, None]:
        deadline = datetime.now(UTC).timestamp() + settings.ticket_qr_stream_max_seconds
        while datetime.now(UTC).timestamp() < deadline:
            now = datetime.now(UTC)
            try:
                inputs = await _resolve_or_deny(
                    db,
                    ticket_id=ticket_id,
                    user_id=user_id,
                    auth_session=auth_session,
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
                user_id=user_id,
                device_id=inputs.device.id,
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
