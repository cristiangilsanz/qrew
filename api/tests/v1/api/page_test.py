import base64
import json

import pytest
from fastapi import HTTPException

from com.qode.qrew.v1.service.core.api.page import (
    clamp_limit,
    decode_cursor,
    encode_cursor,
)


def test_encode_decode_roundtrip() -> None:
    encoded = encode_cursor("2026-01-01T00:00:00Z", "abc-123")
    sort_key, last_id = decode_cursor(encoded)
    assert sort_key == "2026-01-01T00:00:00Z"
    assert last_id == "abc-123"


def test_encoded_cursor_is_url_safe() -> None:
    encoded = encode_cursor("a/b+c=", "id-1")
    assert "+" not in encoded
    assert "/" not in encoded
    assert "=" not in encoded


def test_decode_rejects_garbage() -> None:
    with pytest.raises(HTTPException) as info:
        decode_cursor("not_base64_json!!!")
    assert info.value.status_code == 422


def test_decode_rejects_payload_missing_fields() -> None:
    bogus = (
        base64.urlsafe_b64encode(json.dumps({"sk": 1}).encode()).rstrip(b"=").decode()
    )
    with pytest.raises(HTTPException) as info:
        decode_cursor(bogus)
    assert info.value.status_code == 422


def test_clamp_limit_defaults_when_missing_or_zero() -> None:
    assert clamp_limit(None) == 50
    assert clamp_limit(0) == 50
    assert clamp_limit(-5) == 50


def test_clamp_limit_caps_at_max() -> None:
    assert clamp_limit(1000) == 200
    assert clamp_limit(75) == 75
