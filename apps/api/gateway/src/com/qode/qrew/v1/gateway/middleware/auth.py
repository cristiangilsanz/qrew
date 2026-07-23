"""Gateway JWT authentication middleware.

Validates the Bearer token on every proxied HTTP request and injects
X-Authenticated-User-Id (and X-Authenticated-Token-Type) into the request
so upstream services can trust the identity without re-verifying the JWT.

Public routes (login, register, refresh, passkeys) are passed through
without requiring a token.
"""

import json
import re

import structlog
from starlette.datastructures import MutableHeaders
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send

from com.qode.qrew.v1.gateway.core.auth import (
    _access_public_keys,
    _scanner_public_keys,
    _try_verify,
)

logger = structlog.get_logger(__name__)

# Routes that are accessible without a valid access token.
# Patterns are matched against "METHOD /api/service/path".
_PUBLIC_PATTERNS: list[re.Pattern[str]] = [
    # Identity: auth flows
    re.compile(r"^POST /api/identity/v1/auth/login$"),
    re.compile(r"^POST /api/identity/v1/auth/refresh$"),
    re.compile(r"^POST /api/identity/v1/auth/logout$"),
    re.compile(r"^POST /api/identity/v1/auth/registration/"),
    re.compile(r"^POST /api/identity/v1/auth/passkeys/"),
    re.compile(r"^POST /api/identity/v1/auth/otp/"),
    re.compile(r"^GET  /api/identity/v1/auth/"),
    # Health probes on all services
    re.compile(r"^(GET|HEAD) /api/\w+/v?1?/?health"),
    re.compile(r"^(GET|HEAD) /api/\w+/healthz"),
    re.compile(r"^(GET|HEAD) /api/\w+/ready"),
    re.compile(r"^(GET|HEAD) /health"),
    re.compile(r"^(GET|HEAD) /ready"),
    # CORS preflight
    re.compile(r"^OPTIONS "),
]


def _is_public(method: str, path: str) -> bool:
    key = f"{method} {path}"
    return any(p.match(key) for p in _PUBLIC_PATTERNS)


def _extract_bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer" and parts[1]:
        return parts[1]
    return None


_UNAUTHORIZED = Response(
    content=json.dumps({"detail": {"message": "Missing or invalid token", "field": None}}),
    status_code=401,
    headers={"Content-Type": "application/json"},
)


class AuthMiddleware:
    """ASGI middleware that validates the JWT and injects identity headers."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http",):
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        method = request.method
        path = request.url.path

        # Only intercept proxied API routes
        if not path.startswith("/api/"):
            await self.app(scope, receive, send)
            return

        if _is_public(method, path):
            await self.app(scope, receive, send)
            return

        token = _extract_bearer(request.headers.get("authorization"))
        if token is None:
            await _UNAUTHORIZED(scope, receive, send)
            return

        # Try access token first
        claims = _try_verify(token, _access_public_keys())
        if claims is not None:
            token_type = str(claims.get("type", ""))
            if token_type not in ("access", "setup"):
                await _UNAUTHORIZED(scope, receive, send)
                return
            sub = str(claims.get("sub", ""))
            if not sub:
                await _UNAUTHORIZED(scope, receive, send)
                return
            headers = MutableHeaders(scope=scope)
            headers.append("x-authenticated-user-id", sub)
            headers.append("x-authenticated-token-type", token_type)
            await self.app(scope, receive, send)
            return

        # Try scanner token (for entry service endpoints)
        scanner_keys = _scanner_public_keys()
        if scanner_keys:
            claims = _try_verify(token, scanner_keys)
            if claims is not None and claims.get("type") == "scanner":
                scanner_id = str(claims.get("scanner_id", ""))
                headers = MutableHeaders(scope=scope)
                headers.append("x-authenticated-scanner-id", scanner_id)
                headers.append("x-authenticated-token-type", "scanner")
                await self.app(scope, receive, send)
                return

        await _UNAUTHORIZED(scope, receive, send)
