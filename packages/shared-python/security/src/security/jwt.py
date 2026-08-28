# decodes and verifies the jwts every service signs
from typing import Any

import jwt as pyjwt


# verifies and decodes a signed token
def decode_token(
    token: str,
    public_key: str,
    *,
    algorithms: list[str] | None = None,
    audience: str | None = None,
    issuer: str | None = None,
) -> dict[str, Any]:
    opts: dict[str, Any] = {}
    if audience is not None:
        opts["audience"] = audience
    if issuer is not None:
        opts["issuer"] = issuer
    return pyjwt.decode(  # type: ignore[no-any-return]
        token,
        public_key,
        algorithms=algorithms or ["ES256"],
        **opts,
    )


# reads a token's header without verifying its signature
def decode_unverified_header(token: str) -> dict[str, Any]:
    return pyjwt.get_unverified_header(token)  # type: ignore[no-any-return]
