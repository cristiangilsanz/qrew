import uuid

from middleware.middleware import RequestIDMiddleware, SecurityHeadersMiddleware
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.testclient import TestClient


def _make_app(*middlewares: type) -> Starlette:
    app = Starlette()
    app.add_route("/", lambda req: PlainTextResponse("ok"))
    for mw in reversed(middlewares):
        app.add_middleware(mw)
    return app


class TestRequestIDMiddleware:
    def test_generates_request_id_when_absent(self) -> None:
        client = TestClient(_make_app(RequestIDMiddleware))
        response = client.get("/")
        header = response.headers.get("x-request-id")
        assert header is not None
        uuid.UUID(header)

    def test_echoes_provided_request_id(self) -> None:
        client = TestClient(_make_app(RequestIDMiddleware))
        supplied = str(uuid.uuid4())
        response = client.get("/", headers={"X-Request-ID": supplied})
        assert response.headers.get("x-request-id") == supplied


class TestSecurityHeadersMiddleware:
    def test_sets_all_security_headers(self) -> None:
        client = TestClient(_make_app(SecurityHeadersMiddleware))
        response = client.get("/")
        assert "strict-transport-security" in response.headers
        assert "x-content-type-options" in response.headers
        assert "x-frame-options" in response.headers
        assert "referrer-policy" in response.headers
        assert "permissions-policy" in response.headers

    def test_does_not_overwrite_existing_header(self) -> None:
        from starlette.middleware.base import BaseHTTPMiddleware
        from starlette.requests import Request
        from starlette.responses import Response

        class PresetHeader(BaseHTTPMiddleware):
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
