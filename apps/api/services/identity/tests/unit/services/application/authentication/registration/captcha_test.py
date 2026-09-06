# tests that a registration only gets past the captcha when the check actually ran
import pytest

from com.qode.qrew.v1.identity.core.config import settings
from com.qode.qrew.v1.identity.services.application.authentication.registration import captcha
from com.qode.qrew.v1.identity.services.application.authentication.registration.captcha import (
    CaptchaError,
    CaptchaUnavailableError,
    CloudflareTurnstileCaptchaService,
    StubCaptchaService,
    build_captcha_service,
)


# builds an http client stand in that answers with the given body or fails outright
def _client(body: dict[str, object] | None) -> object:
    class _Response:
        # raises when the stand in was told the service is down
        def raise_for_status(self) -> None:
            if body is None:
                raise RuntimeError("turnstile unreachable")

        # returns the body the stand in was built with
        def json(self) -> dict[str, object]:
            return body or {}

    class _Client:
        # accepts whatever arguments the service passes
        def __init__(self, *args: object, **kwargs: object) -> None:
            del args, kwargs

        # enters the context manager
        async def __aenter__(self) -> "_Client":
            return self

        # leaves the context manager
        async def __aexit__(self, *args: object) -> None:
            del args

        # answers the verification with the prepared response
        async def post(self, *args: object, **kwargs: object) -> _Response:
            del args, kwargs
            return _Response()

    return _Client


class TestBuildCaptchaService:
    # verifies that a disabled captcha yields the stub
    def test_disabled_yields_the_stub(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(settings, "captcha_enabled", False)
        assert isinstance(build_captcha_service(), StubCaptchaService)

    # verifies that an enabled captcha without a key yields the stub
    def test_without_a_key_it_yields_the_stub(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(settings, "captcha_enabled", True)
        monkeypatch.setattr(settings, "captcha_secret_key", "")
        assert isinstance(build_captcha_service(), StubCaptchaService)

    # verifies that a configured captcha yields the real check
    def test_configured_yields_the_real_check(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(settings, "captcha_enabled", True)
        monkeypatch.setattr(settings, "captcha_secret_key", "secret")
        assert isinstance(build_captcha_service(), CloudflareTurnstileCaptchaService)


class TestStubCaptchaService:
    # verifies that the stub lets anything through
    async def test_it_accepts_any_token(self) -> None:
        await StubCaptchaService().verify("whatever", "203.0.113.1")


class TestCloudflareTurnstileCaptchaService:
    # verifies that a token cloudflare accepts passes
    async def test_an_accepted_token_passes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(captcha.httpx, "AsyncClient", _client({"success": True}))
        await CloudflareTurnstileCaptchaService("secret").verify("tok", "203.0.113.1")

    # verifies that a token cloudflare rejects is refused
    async def test_a_rejected_token_is_refused(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            captcha.httpx,
            "AsyncClient",
            _client({"success": False, "error-codes": ["invalid-input-response"]}),
        )
        with pytest.raises(CaptchaError):
            await CloudflareTurnstileCaptchaService("secret").verify("tok", "203.0.113.1")

    # verifies that an unreachable service blocks rather than waving the caller past
    async def test_an_unreachable_service_blocks(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(captcha.httpx, "AsyncClient", _client(None))
        with pytest.raises(CaptchaUnavailableError):
            await CloudflareTurnstileCaptchaService("secret").verify("tok", "203.0.113.1")
