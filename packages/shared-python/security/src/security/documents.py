# validates the identity documents a ticket holder or an account can be named with
import enum
import re

_DNI_RE = re.compile(r"^\d{8}[A-Z]$")
_NIE_RE = re.compile(r"^[XYZ]\d{7}[A-Z]$")
_OTHER_RE = re.compile(r"^[A-Z0-9]{5,20}$")
_LETTER_MAP = "TRWAGMYFPDXBNJZSQVHLCKE"
_NIE_PREFIX = {"X": "0", "Y": "1", "Z": "2"}


class DocumentType(enum.StrEnum):
    dni = "dni"
    nie = "nie"
    other = "other"


# checks the control letter a spanish identity number ends with
def _valid_control_letter(digits: str, letter: str) -> bool:
    return _LETTER_MAP[int(digits) % 23] == letter


# validates a document against the rules of the type it claims to be
def validate_document(value: str, document_type: DocumentType | str) -> str:
    v = value.strip().upper().replace(" ", "").replace("-", "")
    kind = DocumentType(document_type)

    if kind is DocumentType.dni:
        if not _DNI_RE.match(v):
            raise ValueError("A DNI is 8 digits followed by a letter.")
        if not _valid_control_letter(v[:8], v[8]):
            raise ValueError("DNI check letter rejected.")
        return v

    if kind is DocumentType.nie:
        if not _NIE_RE.match(v):
            raise ValueError("A NIE is X, Y or Z followed by 7 digits and a letter.")
        if not _valid_control_letter(_NIE_PREFIX[v[0]] + v[1:8], v[8]):
            raise ValueError("NIE check letter rejected.")
        return v

    # a foreign document has no check digit that holds across every issuing country,
    # so only its shape is checked here and a person reviews the photo behind it
    if not _OTHER_RE.match(v):
        raise ValueError("A document number is 5 to 20 letters or digits.")
    return v


# reports the type a spanish document belongs to when no type was captured with it
def infer_document_type(value: str) -> DocumentType:
    v = value.strip().upper()
    if _DNI_RE.match(v):
        return DocumentType.dni
    if _NIE_RE.match(v):
        return DocumentType.nie
    return DocumentType.other
