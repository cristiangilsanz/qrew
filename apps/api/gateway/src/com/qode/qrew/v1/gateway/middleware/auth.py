# authenticates every proxied request and forwards its identity as headers
import json
import re

import structlog
from starlette.datastructures import MutableHeaders
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send

from com.qode.qrew.v1.gateway.core.config import settings
from com.qode.qrew.v1.gateway.core.auth import (
    user_public_keys,
    scanner_public_keys,
    try_verify,
)

logger = structlog.get_logger(__name__)

_PUBLIC_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^POST /api/identity/v1/auth/login$"),
    re.compile(r"^POST /api/identity/v1/auth/refresh$"),
    re.compile(r"^POST /api/identity/v1/auth/logout$"),
    re.compile(r"^POST /api/identity/v1/auth/registration/"),
    re.compile(r"^POST /api/identity/v1/auth/passkeys/"),
    re.compile(r"^POST /api/identity/v1/auth/otp/"),
    re.compile(r"^POST /api/identity/v1/auth/totp/verify$"),
    re.compile(r"^POST /api/payments/v1/payments/webhook$"),
    re.compile(r"^PUT /api/identity/v1/uploads/local/"),
    re.compile(r"^(GET|HEAD) /api/identity/v1/uploads/public/"),
    re.compile(r"^(GET|HEAD) /api/\w+/v?1?/?health"),
    re.compile(r"^(GET|HEAD) /api/\w+/healthz"),
    re.compile(r"^(GET|HEAD) /api/\w+/ready"),
    re.compile(r"^(GET|HEAD) /health"),
    re.compile(r"^(GET|HEAD) /ready"),
    re.compile(r"^OPTIONS "),
]


# checks whether a request matches one of the routes that skip authentication
def _is_public(method: str, path: str) -> bool:
    key = f"{method} {path}"
    return any(p.match(key) for p in _PUBLIC_PATTERNS)


# reads the bearer token from an authorization header
def _extract_bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer" and parts[1]:
        return parts[1]
    return None


# an account still under review may read the catalogue and finish its own setup
_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
_ALWAYS_ALLOWED_PREFIX = "/api/identity/"

_NOT_VERIFIED = Response(
    content=json.dumps({"detail": {"message": "Account not verified.", "field": None}}),
    status_code=403,
    headers={"Content-Type": "application/json"},
)


# reports whether a caller who has not cleared verification may make this request
def _allowed_while_unverified(method: str, path: str) -> bool:
    return method in _SAFE_METHODS or path.startswith(_ALWAYS_ALLOWED_PREFIX)


_UNAUTHORIZED = Response(
    content=json.dumps({"detail": {"message": "Missing or invalid token", "field": None}}),
    status_code=401,
    headers={"Content-Type": "application/json"},
)


class AuthMiddleware:
    # stores the wrapped asgi application
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    # verifies the request's token and injects the caller's identity headers
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http",):
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        method = request.method
        path = request.url.path

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

        claims = try_verify(token, user_public_keys())
        if claims is not None:
            token_type = str(claims.get("type", ""))
            if token_type not in ("access", "setup"):
                await _UNAUTHORIZED(scope, receive, send)
                return
            sub = str(claims.get("sub", ""))
            if not sub:
                await _UNAUTHORIZED(scope, receive, send)
                return
            verified = claims.get("kyc") is True or claims.get("adm") is True
            if not verified and not _allowed_while_unverified(method, path):
                await _NOT_VERIFIED(scope, receive, send)
                return
            headers = MutableHeaders(scope=scope)
            headers.append("x-authenticated-user-id", sub)
            headers.append("x-authenticated-token-type", token_type)
            if claims.get("adm") is True:
                headers.append("x-authenticated-user-is-admin", "1")
            await self.app(scope, receive, send)
            return

        scanner_keys = scanner_public_keys()
        if scanner_keys:
            claims = try_verify(
                token, scanner_keys, audience_override=settings.scanner_jwt_audience or None
            )
            if claims is not None and claims.get("type") == "scanner":
                scanner_id = str(claims.get("scanner_id", ""))
                headers = MutableHeaders(scope=scope)
                headers.append("x-authenticated-scanner-id", scanner_id)
                headers.append("x-authenticated-token-type", "scanner")
                await self.app(scope, receive, send)
                return

        await _UNAUTHORIZED(scope, receive, send)
