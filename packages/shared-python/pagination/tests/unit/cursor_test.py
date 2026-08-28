# tests cursor
import base64
import json

import pytest
from fastapi import HTTPException
from pagination.cursor import clamp_limit, decode_cursor, encode_cursor


class TestEncodeDecode:
    # verifies that round trip string key
    def test_round_trip_string_key(self) -> None:
        sk, id_ = decode_cursor(encode_cursor("2024-01-01", "uuid-abc"))
        assert sk == "2024-01-01"
        assert id_ == "uuid-abc"

    # verifies that round trip int key
    def test_round_trip_int_key(self) -> None:
        sk, id_ = decode_cursor(encode_cursor(42, "uuid-xyz"))
        assert sk == 42
        assert id_ == "uuid-xyz"

    # verifies that different positions differ
    def test_different_positions_differ(self) -> None:
        c1 = encode_cursor("2024-01-01", "aaa")
        c2 = encode_cursor("2024-01-02", "aaa")
        assert c1 != c2

    # verifies that opaque token no padding
    def test_opaque_token_no_padding(self) -> None:
        token = encode_cursor("sk", "id")
        assert "=" not in token


class TestDecodeCursorErrors:
    # verifies that raises on invalid base64
    def test_raises_on_invalid_base64(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            decode_cursor("!!!not-valid!!!")
        assert exc_info.value.status_code == 422

    # verifies that raises on valid base64 but not json
    def test_raises_on_valid_base64_but_not_json(self) -> None:
        bad = base64.urlsafe_b64encode(b"not-json").decode().rstrip("=")
        with pytest.raises(HTTPException):
            decode_cursor(bad)

    # verifies that raises on missing fields
    def test_raises_on_missing_fields(self) -> None:
        bad = (
            base64.urlsafe_b64encode(json.dumps({"x": 1}).encode()).decode().rstrip("=")
        )
        with pytest.raises(HTTPException):
            decode_cursor(bad)


class TestClampLimit:
    # verifies that none returns default
    def test_none_returns_default(self) -> None:
        assert clamp_limit(None) == 50

    # verifies that zero returns default
    def test_zero_returns_default(self) -> None:
        assert clamp_limit(0) == 50

    # verifies that negative returns default
    def test_negative_returns_default(self) -> None:
        assert clamp_limit(-5) == 50

    # verifies that valid value passes through
    def test_valid_value_passes_through(self) -> None:
        assert clamp_limit(25) == 25

    # verifies that over max is clamped
    def test_over_max_is_clamped(self) -> None:
        assert clamp_limit(999) == 200

    # verifies that exactly max is allowed
    def test_exactly_max_is_allowed(self) -> None:
        assert clamp_limit(200) == 200

    # verifies that custom default
    def test_custom_default(self) -> None:
        assert clamp_limit(None, default=10) == 10
