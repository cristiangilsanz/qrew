from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import Response

from com.qode.qrew.v1.identity.services.auth.auth import get_setup_or_full_user
from com.qode.qrew.v1.identity.services.infra.limiter import limiter
from com.qode.qrew.v1.identity.services.storage import (
    ObjectNotFoundError,
    SignatureExpiredError,
    SignatureInvalidError,
    constraint_for,
    is_valid_key,
    storage,
)
from com.qode.qrew.v1.identity.models.auth.user import User
from com.qode.qrew.v1.identity.schemas.storage.upload import (
    SignUploadRequest,
    SignUploadResponse,
)
from com.qode.qrew.v1.identity.settings import settings

router = APIRouter(prefix="/uploads", tags=["uploads"])


def _user_tenant(user: User) -> str:
    return f"user:{user.id}"


def _bad_request(message: str, field: str | None = None) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={"message": message, "field": field},
    )


@router.post(
    "/sign",
    response_model=SignUploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Mint a signed upload URL for a new object",
)
@limiter.limit("30/minute")  # type: ignore[misc]
async def sign_upload(
    request: Request,
    body: SignUploadRequest,
    current_user: User = Depends(get_setup_or_full_user),
) -> SignUploadResponse:
    """Mint a signed upload URL for a new object."""
    try:
        constraint = constraint_for(body.kind)
    except ValueError as exc:
        raise _bad_request(str(exc), field="kind") from exc
    if body.content_type not in constraint.allowed_content_types:
        raise _bad_request("content_type not allowed", field="content_type")
    if body.size_bytes > constraint.max_size_bytes:
        raise _bad_request("size_bytes exceeds the per-kind limit", field="size_bytes")

    signed = storage.sign_put_url(
        kind=body.kind,
        tenant=_user_tenant(current_user),
        content_type=body.content_type,
        ttl_seconds=settings.storage_signed_url_ttl_seconds,
    )
    return SignUploadResponse(
        key=signed.key,
        upload_url=signed.url,
        expires_at=signed.expires_at,
        max_size_bytes=constraint.max_size_bytes,
    )


@router.put(
    "/local/{key:path}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Accept a signed PUT upload to the local backend",
    include_in_schema=False,
)
async def local_upload(
    request: Request,
    key: str,
    expires_at: Annotated[int, Query(...)],
    sig: Annotated[str, Query(...)],
    content_type: Annotated[str, Query(..., alias="content_type")],
) -> Response:
    """Accept a signed PUT upload to the local backend."""
    if not is_valid_key(key):
        raise _bad_request("invalid key", field="key")
    try:
        await storage.verify_signed_put(key, content_type, expires_at, sig)
    except SignatureExpiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": str(exc), "field": "sig"},
        ) from exc
    except SignatureInvalidError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": str(exc), "field": "sig"},
        ) from exc
    body = await request.body()
    await storage.put(
        kind=storage_kind_for_key(key),
        tenant=storage_tenant_for_key(key),
        content=body,
        content_type=content_type,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/local/{key:path}",
    summary="Serve a signed GET request from the local backend",
    include_in_schema=False,
)
async def local_download(
    key: str,
    expires_at: Annotated[int, Query(...)],
    sig: Annotated[str, Query(...)],
) -> Response:
    """Serve a signed GET request from the local backend."""
    if not is_valid_key(key):
        raise _bad_request("invalid key", field="key")
    try:
        await storage.verify_signed_get(key, expires_at, sig)
    except (SignatureExpiredError, SignatureInvalidError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": str(exc), "field": "sig"},
        ) from exc
    try:
        body = await storage.get(key)
    except ObjectNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "not found", "field": "key"},
        ) from exc
    return Response(content=body, media_type="application/octet-stream")


def storage_kind_for_key(key: str) -> str:
    return key.split("/")[1]


def storage_tenant_for_key(key: str) -> str:
    return key.split("/", maxsplit=1)[0]
