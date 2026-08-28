# checks that uploaded bytes match an accepted file signature
from typing import Final

_ALLOWED_MAGIC: Final[list[bytes]] = [
    b"\xff\xd8\xff",
    b"\x89PNG\r\n\x1a\n",
    b"%PDF-",
]


# checks that content starts with an accepted file signature
def has_allowed_signature(content: bytes) -> bool:
    return any(content.startswith(magic) for magic in _ALLOWED_MAGIC)
