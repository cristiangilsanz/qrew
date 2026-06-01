from com.qode.qrew.v1.service.core.idempotency import compute_fingerprint


def test_identical_requests_produce_identical_fingerprints() -> None:
    body = b'{"amount": 100}'
    a = compute_fingerprint("POST", "/v1/payments", "", body)
    b = compute_fingerprint("POST", "/v1/payments", "", body)
    assert a == b


def test_different_body_changes_fingerprint() -> None:
    a = compute_fingerprint("POST", "/v1/payments", "", b'{"amount": 100}')
    b = compute_fingerprint("POST", "/v1/payments", "", b'{"amount": 200}')
    assert a != b


def test_query_param_order_is_irrelevant() -> None:
    a = compute_fingerprint("POST", "/p", "a=1&b=2", b"")
    b = compute_fingerprint("POST", "/p", "b=2&a=1", b"")
    assert a == b


def test_method_change_changes_fingerprint() -> None:
    a = compute_fingerprint("POST", "/p", "", b"")
    b = compute_fingerprint("DELETE", "/p", "", b"")
    assert a != b
