from fastapi import APIRouter, Depends, Request, status

from com.qode.qrew.v1.service.core.auth.auth import get_current_user
from com.qode.qrew.v1.service.core.infra.limiter import limiter
from com.qode.qrew.v1.service.models.auth.user import User
from com.qode.qrew.v1.service.schemas.auth.session import (
    RevokeAllResponse,
    SessionListResponse,
)
from com.qode.qrew.v1.service.services.session.session import (
    SessionError,
    SessionService,
)

from ._deps import domain_error, get_session_service

router = APIRouter()


@router.get(
    "/sessions",
    response_model=SessionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all active sessions for the current user",
)
@limiter.limit("20/minute")  # type: ignore[misc]
async def list_sessions(
    request: Request,
    current_user: User = Depends(get_current_user),
    service: SessionService = Depends(get_session_service),
) -> SessionListResponse:
    """List all active sessions for the current user."""
    sessions = await service.list_sessions(current_user.id)
    return SessionListResponse(sessions=sessions)


@router.delete(
    "/sessions/{jti}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke a specific session",
)
@limiter.limit("20/minute")  # type: ignore[misc]
async def revoke_session(
    request: Request,
    jti: str,
    current_user: User = Depends(get_current_user),
    service: SessionService = Depends(get_session_service),
) -> None:
    """Revoke a specific session."""
    try:
        await service.revoke_session(jti, current_user.id)
    except SessionError as exc:
        raise domain_error(exc.message, exc.field, status.HTTP_404_NOT_FOUND) from exc


@router.post(
    "/sessions/revoke-all",
    response_model=RevokeAllResponse,
    status_code=status.HTTP_200_OK,
    summary="Revoke all sessions for the current user",
)
@limiter.limit("10/minute")  # type: ignore[misc]
async def revoke_all_sessions(
    request: Request,
    current_user: User = Depends(get_current_user),
    service: SessionService = Depends(get_session_service),
) -> RevokeAllResponse:
    """Revoke all sessions for the current user."""
    await service.revoke_all(current_user.id)
    return RevokeAllResponse(message="All sessions have been revoked.")
