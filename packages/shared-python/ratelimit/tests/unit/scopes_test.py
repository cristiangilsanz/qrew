# tests scopes
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from ratelimit.scopes import build_scope_key, resolve_scope_value


class TestBuildScopeKey:
    # verifies that formats key
    def test_formats_key(self) -> None:
        assert build_scope_key("ip", "1.2.3.4") == "ip:1.2.3.4"

    # verifies that user scope
    def test_user_scope(self) -> None:
        assert build_scope_key("user", "uuid-abc") == "user:uuid-abc"


class TestResolveScopeValue:
    # handles make request
    def _make_request(
        self,
        *,
        forwarded: str | None = None,
        client_host: str | None = "1.2.3.4",
        user_id: object = None,
        device_id: object = None,
        fingerprint: str | None = None,
        org_id: str | None = None,
    ) -> MagicMock:
        req = MagicMock()
        headers: dict[str, str] = {}
        if forwarded:
            headers["X-Forwarded-For"] = forwarded
        if fingerprint:
            headers["X-Device-Fingerprint"] = fingerprint
        req.headers = headers
        req.client = MagicMock()
        req.client.host = client_host
        req.state = SimpleNamespace(
            current_user_id=user_id,
            current_device_id=device_id,
        )
        req.path_params = {"organisation_id": org_id} if org_id else {}
        return req

    # verifies that a forwarded header from the trusted proxy is honoured
    async def test_ip_from_forwarded_header_behind_the_trusted_proxy(self) -> None:
        req = self._make_request(
            forwarded="10.0.0.1, 172.0.0.1", client_host="192.0.2.7"
        )
        result = await resolve_scope_value("ip", req, trusted_proxy_ip="192.0.2.7")
        assert result == "10.0.0.1"

    # verifies that a forwarded header from anywhere else is ignored
    async def test_ip_ignores_a_forwarded_header_from_an_untrusted_hop(self) -> None:
        req = self._make_request(forwarded="10.0.0.1", client_host="198.51.100.9")
        result = await resolve_scope_value("ip", req, trusted_proxy_ip="192.0.2.7")
        assert result == "198.51.100.9"

    # verifies that a forwarded header is ignored when no proxy is trusted
    async def test_ip_ignores_a_forwarded_header_with_no_proxy(self) -> None:
        req = self._make_request(forwarded="10.0.0.1", client_host="198.51.100.9")
        result = await resolve_scope_value("ip", req)
        assert result == "198.51.100.9"

    # verifies that a spoofed header cannot split one caller into two buckets
    async def test_a_spoofed_header_cannot_change_the_scope_key(self) -> None:
        first = self._make_request(forwarded="1.1.1.1", client_host="198.51.100.9")
        second = self._make_request(forwarded="2.2.2.2", client_host="198.51.100.9")
        assert await resolve_scope_value("ip", first) == await resolve_scope_value(
            "ip", second
        )

    # verifies that ip from client
    async def test_ip_from_client(self) -> None:
        req = self._make_request(client_host="5.5.5.5")
        result = await resolve_scope_value("ip", req)
        assert result == "5.5.5.5"

    # verifies that user scope with user
    async def test_user_scope_with_user(self) -> None:
        req = self._make_request(user_id="uid-123")
        result = await resolve_scope_value("user", req)
        assert result == "uid-123"

    # verifies that user scope no user
    async def test_user_scope_no_user(self) -> None:
        req = self._make_request(user_id=None)
        result = await resolve_scope_value("user", req)
        assert result is None

    # verifies that device scope
    async def test_device_scope(self) -> None:
        req = self._make_request(device_id="dev-456")
        result = await resolve_scope_value("device", req)
        assert result == "dev-456"

    # verifies that fingerprint scope
    async def test_fingerprint_scope(self) -> None:
        req = self._make_request(fingerprint="fp-abc")
        result = await resolve_scope_value("fingerprint", req)
        assert result == "fp-abc"

    # verifies that org scope
    async def test_org_scope(self) -> None:
        req = self._make_request(org_id="org-789")
        result = await resolve_scope_value("org", req)
        assert result == "org-789"

    # verifies that unknown scope raises
    async def test_unknown_scope_raises(self) -> None:
        req = self._make_request()
        with pytest.raises(ValueError, match="unknown"):
            await resolve_scope_value("unknown", req)
