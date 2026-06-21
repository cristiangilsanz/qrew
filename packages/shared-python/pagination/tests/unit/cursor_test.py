import base64
import json

import pytest
from fastapi import HTTPException

from pagination.cursor import clamp_limit, decode_cursor, encode_cursor


class TestEncodeDecode:
    def test_round_trip_string_key(self) -> None:
        sk, id_ = decode_cursor(encode_cursor("2024-01-01", "uuid-abc"))
        assert sk == "2024-01-01"
        assert id_ == "uuid-abc"

    def test_round_trip_int_key(self) -> None:
        sk, id_ = decode_cursor(encode_cursor(42, "uuid-xyz"))
        assert sk == 42
        assert id_ == "uuid-xyz"

    def test_different_positions_differ(self) -> None:
        c1 = encode_cursor("2024-01-01", "aaa")
        c2 = encode_cursor("2024-01-02", "aaa")
        assert c1 != c2

    def test_opaque_token_no_padding(self) -> None:
        token = encode_cursor("sk", "id")
        assert "=" not in token


class TestDecodeCursorErrors:
    def test_raises_on_invalid_base64(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            decode_cursor("!!!not-valid!!!")
        assert exc_info.value.status_code == 422

    def test_raises_on_valid_base64_but_not_json(self) -> None:
        bad = base64.urlsafe_b64encode(b"not-json").decode().rstrip("=")
        with pytest.raises(HTTPException):
            decode_cursor(bad)

    def test_raises_on_missing_fields(self) -> None:
        bad = base64.urlsafe_b64encode(json.dumps({"x": 1}).encode()).decode().rstrip("=")
        with pytest.raises(HTTPException):
            decode_cursor(bad)


class TestClampLimit:
    def test_none_returns_default(self) -> None:
        assert clamp_limit(None) == 50

    def test_zero_returns_default(self) -> None:
        assert clamp_limit(0) == 50

    def test_negative_returns_default(self) -> None:
        assert clamp_limit(-5) == 50

    def test_valid_value_passes_through(self) -> None:
        assert clamp_limit(25) == 25

    def test_over_max_is_clamped(self) -> None:
        assert clamp_limit(999) == 200

    def test_exactly_max_is_allowed(self) -> None:
        assert clamp_limit(200) == 200

    def test_custom_default(self) -> None:
        assert clamp_limit(None, default=10) == 10
