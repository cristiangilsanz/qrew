import hashlib
from urllib.parse import parse_qsl, urlencode


def compute_fingerprint(method: str, path: str, query_string: str, body: bytes) -> str:
    sorted_query = urlencode(sorted(parse_qsl(query_string, keep_blank_values=True)))
    digest = hashlib.sha256()
    digest.update(method.upper().encode())
    digest.update(b"|")
    digest.update(path.encode())
    digest.update(b"|")
    digest.update(sorted_query.encode())
    digest.update(b"|")
    digest.update(hashlib.sha256(body).digest())
    return digest.hexdigest()
