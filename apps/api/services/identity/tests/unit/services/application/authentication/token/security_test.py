# covers password hashing breach checks and the tokens every auth flow issues
from datetime import UTC, datetime

import pytest

from com.qode.qrew.v1.identity.core.config import settings
from com.qode.qrew.v1.identity.core.utils import jwt as jwt_keys
from com.qode.qrew.v1.identity.services.application.authentication.token import security


class TestPasswordHashing:
    # verifies that a password verifies against its own hash
    def test_a_password_verifies_against_its_hash(self) -> None:
        hashed = security.hash_password("correct horse battery staple")
        assert security.verify_password("correct horse battery staple", hashed) is True

    # verifies that a wrong password does not verify
    def test_a_wrong_password_does_not_verify(self) -> None:
        hashed = security.hash_password("correct horse battery staple")
        assert security.verify_password("something else", hashed) is False

    # verifies that the same password hashes differently every time
    def test_the_same_password_hashes_differently_each_time(self) -> None:
        assert security.hash_password("a strong one") != security.hash_password("a strong one")


class TestIsPasswordPwned:
    # verifies that the check stands down when it is turned off
    async def test_it_stands_down_when_disabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(settings, "hibp_enabled", False)
        assert await security.is_password_pwned("password") is False

    # verifies that a breached password is reported
    async def test_a_breached_password_is_reported(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import hashlib

        suffix = hashlib.sha1(b"password", usedforsecurity=False).hexdigest().upper()[5:]
        monkeypatch.setattr(settings, "hibp_enabled", True)
        monkeypatch.setattr(
            security.httpx, "AsyncClient", _client_answering(f"{suffix}:42\nAAAAA:1")
        )
        assert await security.is_password_pwned("password") is True

    # verifies that a password absent from the range is not reported
    async def test_an_unseen_password_is_not_reported(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "hibp_enabled", True)
        monkeypatch.setattr(security.httpx, "AsyncClient", _client_answering("AAAAA:1"))
        assert await security.is_password_pwned("password") is False

    # verifies that an unreachable service lets the password through
    async def test_an_unreachable_service_lets_it_through(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "hibp_enabled", True)
        monkeypatch.setattr(security.httpx, "AsyncClient", _client_answering(None))
        assert await security.is_password_pwned("password") is False


# builds an http client stand in that answers with the given text or fails
def _client_answering(text: str | None) -> object:
    class _Response:
        # raises when the stand in was told to fail
        def raise_for_status(self) -> None:
            if text is None:
                raise RuntimeError("service down")

        @property
        # returns the body the stand in was built with
        def text(self) -> str:
            return text or ""

    class _Client:
        # accepts whatever arguments the caller passes
        def __init__(self, *args: object, **kwargs: object) -> None:
            del args, kwargs

        # enters the context manager
        async def __aenter__(self) -> "_Client":
            return self

        # leaves the context manager
        async def __aexit__(self, *args: object) -> None:
            del args

        # answers the range query with the prepared response
        async def get(self, *args: object, **kwargs: object) -> _Response:
            del args, kwargs
            return _Response()

    return _Client


class TestGenerators:
    # verifies that a generated token is unique and url safe
    def test_a_generated_token_is_unique_and_url_safe(self) -> None:
        first, second = security.generate_token(), security.generate_token()
        assert first != second
        assert "/" not in first and "+" not in first

    # verifies that a one time code has the requested length and only digits
    def test_a_one_time_code_is_all_digits(self) -> None:
        code = security.generate_otp()
        assert len(code) == 6
        assert code.isdigit()

    # verifies that a one time code honours a requested length
    def test_a_one_time_code_honours_its_length(self) -> None:
        assert len(security.generate_otp(8)) == 8


class TestExpiries:
    # verifies that both expiries land in the future
    def test_both_expiries_land_in_the_future(self) -> None:
        now = datetime.now(UTC)
        assert security.email_verification_token_expiry() > now
        assert security.phone_number_otp_expiry() > now


class TestTokens:
    # verifies that an access token names its subject and scope
    def test_an_access_token_names_its_subject_and_scope(self) -> None:
        claims = jwt_keys.verify(jwt_keys.ACCESS, security.create_access_token("user-1"))
        assert claims["sub"] == "user-1"
        assert claims["scope"] == "access"

    # verifies that an ordinary access token claims neither role
    def test_an_ordinary_access_token_claims_no_role(self) -> None:
        claims = jwt_keys.verify(jwt_keys.ACCESS, security.create_access_token("user-1"))
        assert "adm" not in claims
        assert "kyc" not in claims

    # verifies that an access token carries the roles and identifiers it was given
    def test_an_access_token_carries_what_it_was_given(self) -> None:
        token = security.create_access_token(
            "user-1",
            device_id="device-1",
            session_jti="session-1",
            is_admin=True,
            kyc_approved=True,
        )
        claims = jwt_keys.verify(jwt_keys.ACCESS, token)
        assert claims["adm"] is True
        assert claims["kyc"] is True
        assert claims["device_id"] == "device-1"
        assert claims["jti"] == "session-1"

    # verifies that each flow signs its token with its own key and scope
    @pytest.mark.parametrize(
        ("factory", "purpose", "scope"),
        [
            (security.create_setup_token, jwt_keys.SETUP, "setup"),
            (security.create_recovery_token, jwt_keys.RECOVERY, "recovery"),
            (security.create_totp_token, jwt_keys.TOTP, "totp"),
        ],
    )
    def test_each_flow_signs_with_its_own_key(
        self, factory: object, purpose: str, scope: str
    ) -> None:
        claims = jwt_keys.verify(purpose, factory("user-1"))  # type: ignore[operator]
        assert claims["sub"] == "user-1"
        assert claims["scope"] == scope

    # verifies that a refresh token carries a session identifier that decodes back
    def test_a_refresh_token_carries_a_session_identifier(self) -> None:
        token = security.create_refresh_token("user-1")
        claims = security.decode_refresh_token(token)
        assert claims["type"] == "refresh"
        assert security.extract_jti(token) == claims["jti"]

    # verifies that two refresh tokens name different sessions
    def test_two_refresh_tokens_name_different_sessions(self) -> None:
        first = security.extract_jti(security.create_refresh_token("user-1"))
        second = security.extract_jti(security.create_refresh_token("user-1"))
        assert first != second
