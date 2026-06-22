import base64
import binascii
import json
from typing import Any

from fastapi import HTTPException
from starlette.status import HTTP_422_UNPROCESSABLE_CONTENT

DEFAULT_LIMIT = 50
MAX_LIMIT = 200


def encode_cursor(sort_key: Any, last_id: str) -> str:
    """Encodes a pagination position as an opaque URL-safe token."""
    payload = json.dumps({"sk": sort_key, "id": last_id}, default=str)
    return base64.urlsafe_b64encode(payload.encode()).rstrip(b"=").decode()


def decode_cursor(raw: str) -> tuple[Any, str]:
    """Decodes a pagination token, raising an HTTP error on malformed input."""
    padded = raw + "=" * (-len(raw) % 4)
    try:
        decoded = base64.urlsafe_b64decode(padded).decode()
        payload = json.loads(decoded)
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"message": "Malformed cursor", "field": "cursor"},
        ) from exc
    if not isinstance(payload, dict) or "sk" not in payload or "id" not in payload:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"message": "Malformed cursor", "field": "cursor"},
        )
    payload_dict: dict[str, Any] = payload  # type: ignore[no-redef]
    return payload_dict["sk"], str(payload_dict["id"])


def clamp_limit(limit: int | None, default: int = DEFAULT_LIMIT) -> int:
    """Clamps a client-supplied page size into the accepted range."""
    if limit is None or limit <= 0:
        return default
    return min(limit, MAX_LIMIT)
