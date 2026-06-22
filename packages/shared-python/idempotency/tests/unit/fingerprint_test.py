from idempotency.fingerprint import compute_fingerprint


class TestComputeFingerprint:
    def test_deterministic(self) -> None:
        h1 = compute_fingerprint("POST", "/orders", "", b'{"amount":100}')
        h2 = compute_fingerprint("POST", "/orders", "", b'{"amount":100}')
        assert h1 == h2

    def test_method_case_normalised(self) -> None:
        h1 = compute_fingerprint("POST", "/orders", "", b"body")
        h2 = compute_fingerprint("post", "/orders", "", b"body")
        assert h1 == h2

    def test_different_methods_differ(self) -> None:
        h1 = compute_fingerprint("POST", "/orders", "", b"body")
        h2 = compute_fingerprint("PUT", "/orders", "", b"body")
        assert h1 != h2

    def test_different_paths_differ(self) -> None:
        h1 = compute_fingerprint("GET", "/a", "", b"")
        h2 = compute_fingerprint("GET", "/b", "", b"")
        assert h1 != h2

    def test_different_bodies_differ(self) -> None:
        h1 = compute_fingerprint("POST", "/x", "", b"body1")
        h2 = compute_fingerprint("POST", "/x", "", b"body2")
        assert h1 != h2

    def test_query_params_sorted(self) -> None:
        h1 = compute_fingerprint("GET", "/search", "b=2&a=1", b"")
        h2 = compute_fingerprint("GET", "/search", "a=1&b=2", b"")
        assert h1 == h2

    def test_different_query_differ(self) -> None:
        h1 = compute_fingerprint("GET", "/search", "a=1", b"")
        h2 = compute_fingerprint("GET", "/search", "a=2", b"")
        assert h1 != h2

    def test_returns_hex_string(self) -> None:
        result = compute_fingerprint("GET", "/", "", b"")
        assert len(result) == 64
        int(result, 16)
