from typing import Any

import jwt as pyjwt


def decode_token(
    token: str,
    public_key: str,
    *,
    algorithms: list[str] | None = None,
    audience: str | None = None,
) -> dict[str, Any]:
    """Decodes and verifies a JWT, returning its claims on success."""
    opts: dict[str, Any] = {}
    if audience is not None:
        opts["audience"] = audience
    return pyjwt.decode(  # type: ignore[no-any-return]
        token,
        public_key,
        algorithms=algorithms or ["ES256"],
        **opts,
    )


def decode_unverified_header(token: str) -> dict[str, Any]:
    """Extracts the JWT header without verifying the signature."""
    return pyjwt.get_unverified_header(token)  # type: ignore[no-any-return]
