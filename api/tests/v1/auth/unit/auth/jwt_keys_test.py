"""Tests for the per-purpose JWT signing/verification module."""

import jwt
import pytest

from com.qode.qrew.v1.service.core.auth import jwt_keys


def _claims() -> dict[str, object]:
    return {"sub": "user-123"}


def test_sign_then_verify_roundtrip_per_purpose() -> None:
    for purpose in jwt_keys.PURPOSES:
        token = jwt_keys.sign(purpose, _claims())
        payload = jwt_keys.verify(purpose, token)
        assert payload["sub"] == "user-123"


def test_each_purpose_has_a_distinct_kid() -> None:
    kids = {jwt_keys.kid_for(p) for p in jwt_keys.PURPOSES}
    assert len(kids) == len(jwt_keys.PURPOSES)


def test_sign_includes_kid_header_for_purpose() -> None:
    token = jwt_keys.sign(jwt_keys.ACCESS, _claims())
    header = jwt.get_unverified_header(token)
    assert header["kid"] == jwt_keys.kid_for(jwt_keys.ACCESS)
    assert header["alg"] == jwt_keys.ALGORITHM


def test_verify_rejects_token_signed_for_a_different_purpose() -> None:
    setup_token = jwt_keys.sign(jwt_keys.SETUP, _claims())
    with pytest.raises(jwt.InvalidTokenError):
        jwt_keys.verify(jwt_keys.ACCESS, setup_token)


def test_verify_any_returns_matching_purpose() -> None:
    token = jwt_keys.sign(jwt_keys.SETUP, _claims())
    matched, payload = jwt_keys.verify_any((jwt_keys.ACCESS, jwt_keys.SETUP), token)
    assert matched == jwt_keys.SETUP
    assert payload["sub"] == "user-123"


def test_verify_any_rejects_unknown_kid() -> None:
    refresh_token = jwt_keys.sign(jwt_keys.REFRESH, _claims())
    with pytest.raises(jwt.InvalidTokenError):
        jwt_keys.verify_any((jwt_keys.ACCESS, jwt_keys.SETUP), refresh_token)


def test_tampered_token_fails_verification() -> None:
    token = jwt_keys.sign(jwt_keys.ACCESS, _claims())
    tampered = token[:-4] + ("AAAA" if not token.endswith("AAAA") else "BBBB")
    with pytest.raises(jwt.InvalidTokenError):
        jwt_keys.verify(jwt_keys.ACCESS, tampered)
