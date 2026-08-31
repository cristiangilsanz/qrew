# checks that uploaded bytes match an accepted file signature
from typing import Final

_ALLOWED_MAGIC: Final[list[bytes]] = [
    b"\xff\xd8\xff",
    b"\x89PNG\r\n\x1a\n",
    b"%PDF-",
]

_HEIF_BRANDS: Final[frozenset[bytes]] = frozenset(
    {
        b"heic",
        b"heix",
        b"hevc",
        b"hevx",
        b"heim",
        b"heis",
        b"hevm",
        b"hevs",
        b"mif1",
        b"msf1",
    }
)


# checks that content starts with an accepted file signature
def has_allowed_signature(content: bytes) -> bool:
    if any(content.startswith(magic) for magic in _ALLOWED_MAGIC):
        return True
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return True
    return content[4:8] == b"ftyp" and content[8:12] in _HEIF_BRANDS
