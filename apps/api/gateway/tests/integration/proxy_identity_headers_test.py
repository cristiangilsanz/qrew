# tests that the gateway never forwards an identity header a client made up
import uuid
from typing import Any

import httpx
import pytest
from starlette.testclient import TestClient

from com.qode.qrew.v1.gateway.app import app
from com.qode.qrew.v1.gateway.middleware.auth import (
    is_spoofable_header,
    scrub_spoofable_headers,
)

_VICTIM = str(uuid.uuid4())


class _Recorder:
    # stands in for the upstream http client and keeps the headers it was given
    def __init__(self) -> None:
        self.headers: httpx.Headers = httpx.Headers()

    # records the forwarded headers and answers with an empty json body
    async def request(self, **kwargs: Any) -> httpx.Response:
        self.headers = httpx.Headers(kwargs["headers"])
        return httpx.Response(200, json={})


# replaces the proxy's upstream client so the forwarded headers can be inspected
@pytest.fixture
def upstream(client: TestClient) -> _Recorder:
    recorder = _Recorder()
    previous = getattr(app.state, "proxy_client", None)
    app.state.proxy_client = recorder
    yield recorder  # type: ignore[misc]
    app.state.proxy_client = previous


# a public route must not let an unauthenticated caller name themselves
def test_public_route_drops_forged_user_id(client: TestClient, upstream: _Recorder) -> None:
    response = client.post(
        "/api/identity/v1/auth/passkeys/authenticate/begin",
        headers={"x-authenticated-user-id": _VICTIM},
        json={"email": "victim@qrew.dev"},
    )

    assert response.status_code == 200
    assert "x-authenticated-user-id" not in upstream.headers


# the routes that act on an account are no longer waved through unauthenticated
@pytest.mark.parametrize(
    "path",
    [
        "/api/identity/v1/auth/passkeys/register/begin",
        "/api/identity/v1/auth/passkeys/register/complete",
        "/api/identity/v1/auth/passkeys/assert/begin",
        "/api/identity/v1/auth/registration/verify-phone",
    ],
)
def test_account_routes_require_a_token(client: TestClient, path: str) -> None:
    response = client.post(path, headers={"x-authenticated-user-id": _VICTIM}, json={})

    assert response.status_code == 401


# a caller holding a real token must not be able to speak for a different account
def test_protected_route_overrides_forged_user_id(
    client: TestClient, upstream: _Recorder, access_token_factory: Any
) -> None:
    caller = str(uuid.uuid4())

    response = client.get(
        "/api/catalog/v1/events",
        headers={
            "Authorization": f"Bearer {access_token_factory(caller)}",
            "x-authenticated-user-id": _VICTIM,
        },
    )

    assert response.status_code == 200
    assert upstream.headers.get_list("x-authenticated-user-id") == [caller]


# a caller must not be able to promote themselves by claiming to be an admin
def test_forged_admin_flag_is_dropped(
    client: TestClient, upstream: _Recorder, access_token_factory: Any
) -> None:
    response = client.get(
        "/api/catalog/v1/events",
        headers={
            "Authorization": f"Bearer {access_token_factory(str(uuid.uuid4()))}",
            "x-authenticated-user-is-admin": "1",
        },
    )

    assert response.status_code == 200
    assert "x-authenticated-user-is-admin" not in upstream.headers


# a caller must not be able to pass themselves off as a control device
def test_forged_scanner_id_is_dropped(
    client: TestClient, upstream: _Recorder, access_token_factory: Any
) -> None:
    response = client.get(
        "/api/entry/v1/scans",
        headers={
            "Authorization": f"Bearer {access_token_factory(str(uuid.uuid4()))}",
            "x-authenticated-scanner-id": str(uuid.uuid4()),
        },
    )

    assert response.status_code == 200
    assert "x-authenticated-scanner-id" not in upstream.headers


# the key that guards the service to service routes never travels in from outside
def test_client_internal_key_is_dropped(
    client: TestClient, upstream: _Recorder, access_token_factory: Any
) -> None:
    response = client.get(
        "/api/identity/_internal/users/lookup",
        headers={
            "Authorization": f"Bearer {access_token_factory(str(uuid.uuid4()))}",
            "X-Internal-Key": "guessed-secret",
        },
    )

    assert response.status_code == 200
    assert "x-internal-key" not in upstream.headers


# every header the gateway owns is recognised whatever case the client wrote it in
@pytest.mark.parametrize(
    "name",
    [
        "x-authenticated-user-id",
        "X-Authenticated-User-Id",
        "X-AUTHENTICATED-SCANNER-ID",
        "x-authenticated-token-type",
        "X-Internal-Key",
    ],
)
def test_spoofable_header_names(name: str) -> None:
    assert is_spoofable_header(name)


# headers the client legitimately owns are left alone
@pytest.mark.parametrize("name", ["authorization", "content-type", "x-request-id", "x-device-id"])
def test_untouched_header_names(name: str) -> None:
    assert not is_spoofable_header(name)


# scrubbing removes only the forged headers and leaves the rest of the request intact
def test_scrub_keeps_the_other_headers() -> None:
    scope: dict[str, Any] = {
        "headers": [
            (b"authorization", b"Bearer t"),
            (b"x-authenticated-user-id", _VICTIM.encode()),
            (b"X-Internal-Key", b"guessed"),
            (b"content-type", b"application/json"),
        ]
    }

    dropped = scrub_spoofable_headers(scope)

    assert sorted(dropped) == ["X-Internal-Key", "x-authenticated-user-id"]
    assert scope["headers"] == [
        (b"authorization", b"Bearer t"),
        (b"content-type", b"application/json"),
    ]


# verifies that the recovery ceremony reaches identity with its own token intact
@pytest.mark.parametrize("step", ["begin", "complete"])
def test_recovery_is_public_so_its_own_token_survives(step: str) -> None:
    from com.qode.qrew.v1.gateway.middleware.auth import _is_public

    assert _is_public("POST", f"/api/identity/v1/auth/recovery/{step}")


# verifies that no other recovery route was opened by that pattern
def test_recovery_opens_no_other_route() -> None:
    from com.qode.qrew.v1.gateway.middleware.auth import _is_public

    assert not _is_public("POST", "/api/identity/v1/auth/recovery/anything-else")
    assert not _is_public("GET", "/api/identity/v1/auth/recovery/begin")
