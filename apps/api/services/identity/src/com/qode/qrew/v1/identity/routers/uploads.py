# exposes the endpoints that sign and serve uploads to the local storage backend
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import Response

from com.qode.qrew.v1.identity.core.dependencies import get_setup_or_full_user
from com.qode.qrew.v1.identity.core.dependencies import limiter
from com.qode.qrew.v1.identity.services.application.storage import (
    ObjectNotFoundError,
    SignatureExpiredError,
    SignatureInvalidError,
    constraint_for,
    has_allowed_signature,
    is_valid_key,
    storage,
)
from com.qode.qrew.v1.identity.models.user import User
from com.qode.qrew.v1.identity.schemas.storage.upload import (
    SignUploadRequest,
    SignUploadResponse,
)
from com.qode.qrew.v1.identity.core.config import settings

router = APIRouter(prefix="/uploads", tags=["uploads"])


# derives the storage tenant scope for a user
def _user_tenant(user: User) -> str:
    return f"user:{user.id}"


# builds a bad request response with a message and field
def _bad_request(message: str, field: str | None = None) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={"message": message, "field": field},
    )


# mints a signed url the caller can upload a new object to
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


# accepts a signed upload and stores it in the local backend
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
    if await storage.exists(key):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "Object already stored.", "field": "key"},
        )
    body = await request.body()
    try:
        constraint = constraint_for(storage_kind_for_key(key))
        if len(body) > constraint.max_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail={"message": "Payload exceeds the size limit."},
            )
    except ValueError:
        pass
    if not has_allowed_signature(body):
        raise _bad_request("payload is not an accepted file type", field="body")
    await storage.store_at(key, body, content_type)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# serves a signed download from the local backend
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
            detail={"message": "Object not found.", "field": "key"},
        ) from exc
    return Response(content=body, media_type="application/octet-stream")


# serves a public event image without authentication
@router.get(
    "/public/{key:path}",
    summary="Serve a public event image (no auth required)",
    include_in_schema=False,
)
async def public_image(key: str) -> Response:
    if not is_valid_key(key):
        raise _bad_request("invalid key", field="key")
    if storage_kind_for_key(key) != "event_image":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not public")
    try:
        body = await storage.get(key)
    except ObjectNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Object not found.", "field": "key"},
        ) from exc
    return Response(
        content=body,
        media_type=_detect_image_type(body),
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


# sniffs an image's content type from its leading bytes
def _detect_image_type(data: bytes) -> str:
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return "application/octet-stream"


# reads the storage kind embedded in an object key
def storage_kind_for_key(key: str) -> str:
    return key.split("/")[1]


# reads the tenant scope embedded in an object key
def storage_tenant_for_key(key: str) -> str:
    return key.split("/", maxsplit=1)[0]
