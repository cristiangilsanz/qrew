from collections.abc import Awaitable, Callable

from fastapi import Request

ScopeResolver = Callable[[Request], Awaitable[str | None]]

ALLOWED_SCOPES = frozenset({"ip", "user", "device", "fingerprint", "org"})


async def _resolve_ip(request: Request) -> str | None:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    return request.client.host if request.client else None


async def _resolve_user(request: Request) -> str | None:
    user = getattr(request.state, "current_user_id", None)
    return str(user) if user else None


async def _resolve_device(request: Request) -> str | None:
    device = getattr(request.state, "current_device_id", None)
    return str(device) if device else None


async def _resolve_fingerprint(request: Request) -> str | None:
    return request.headers.get("X-Device-Fingerprint")


async def _resolve_org(request: Request) -> str | None:
    org_id = request.path_params.get("organisation_id")
    return str(org_id) if org_id else None


_RESOLVERS: dict[str, ScopeResolver] = {
    "ip": _resolve_ip,
    "user": _resolve_user,
    "device": _resolve_device,
    "fingerprint": _resolve_fingerprint,
    "org": _resolve_org,
}


async def resolve_scope_value(scope: str, request: Request) -> str | None:
    """Return the runtime value for a scope on the current request."""
    if scope not in _RESOLVERS:
        raise ValueError(f"unknown rate-limit scope: {scope}")
    return await _RESOLVERS[scope](request)


def build_scope_key(scope: str, value: str) -> str:
    """Produce the Redis key fragment for a scope and its runtime value."""
    return f"{scope}:{value}"
