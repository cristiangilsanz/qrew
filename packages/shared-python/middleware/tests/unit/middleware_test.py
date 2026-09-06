# tests middleware
import uuid

from middleware.middleware import (
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
    client_ip,
)
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.testclient import TestClient


# handles make app
def _make_app(*middlewares: type) -> Starlette:
    app = Starlette()
    app.add_route("/", lambda req: PlainTextResponse("ok"))
    for mw in reversed(middlewares):
        app.add_middleware(mw)
    return app


class TestRequestIDMiddleware:
    # verifies that generates request id when absent
    def test_generates_request_id_when_absent(self) -> None:
        client = TestClient(_make_app(RequestIDMiddleware))
        response = client.get("/")
        header = response.headers.get("x-request-id")
        assert header is not None
        uuid.UUID(header)

    # verifies that echoes provided request id
    def test_echoes_provided_request_id(self) -> None:
        client = TestClient(_make_app(RequestIDMiddleware))
        supplied = str(uuid.uuid4())
        response = client.get("/", headers={"X-Request-ID": supplied})
        assert response.headers.get("x-request-id") == supplied


class TestSecurityHeadersMiddleware:
    # verifies that sets all security headers
    def test_sets_all_security_headers(self) -> None:
        client = TestClient(_make_app(SecurityHeadersMiddleware))
        response = client.get("/")
        assert "strict-transport-security" in response.headers
        assert "x-content-type-options" in response.headers
        assert "x-frame-options" in response.headers
        assert "referrer-policy" in response.headers
        assert "permissions-policy" in response.headers
        assert "content-security-policy" in response.headers

    # verifies that does not overwrite existing header
    def test_does_not_overwrite_existing_header(self) -> None:
        from starlette.middleware.base import BaseHTTPMiddleware
        from starlette.requests import Request
        from starlette.responses import Response

        class PresetHeader(BaseHTTPMiddleware):
            # handles dispatch
            async def dispatch(self, request: Request, call_next: object) -> Response:
                import collections.abc

                assert callable(call_next)
                assert isinstance(call_next, collections.abc.Callable)
                response = await call_next(request)  # type: ignore[operator]
                response.headers["X-Frame-Options"] = "SAMEORIGIN"
                return response

        app = _make_app(SecurityHeadersMiddleware, PresetHeader)  # type: ignore[arg-type]
        client = TestClient(app)
        response = client.get("/")
        assert response.headers.get("x-frame-options") == "SAMEORIGIN"


class TestClientIp:
    # verifies that returns the direct peer without a trusted proxy
    def test_returns_the_direct_peer_without_a_trusted_proxy(self) -> None:
        request = _request(client="203.0.113.5", forwarded="198.51.100.9")
        assert client_ip(request) == "203.0.113.5"

    # verifies that ignores the header from an untrusted peer
    def test_ignores_the_header_from_an_untrusted_peer(self) -> None:
        request = _request(client="203.0.113.5", forwarded="198.51.100.9")
        assert client_ip(request, trusted_proxy_ip="10.0.0.1") == "203.0.113.5"

    # verifies that takes the first hop from a trusted peer
    def test_takes_the_first_hop_from_a_trusted_peer(self) -> None:
        request = _request(client="10.0.0.1", forwarded="198.51.100.9, 10.0.0.1")
        assert client_ip(request, trusted_proxy_ip="10.0.0.1") == "198.51.100.9"


# handles request
def _request(*, client: str, forwarded: str | None) -> Request:
    headers = [(b"x-forwarded-for", forwarded.encode())] if forwarded else []
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": headers,
        "client": (client, 12345),
    }
    return Request(scope)
