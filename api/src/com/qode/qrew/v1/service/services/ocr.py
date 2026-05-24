import io
import re

import cv2
import numpy as np
import pytesseract  # type: ignore[import-untyped]
import structlog
from PIL import Image

logger = structlog.get_logger(__name__)

# DNI: 8 digits + 1 letter (not I/O/U).  NIE: X/Y/Z + 7 digits + 1 letter.
ID_PATTERN = re.compile(
    r"\b([0-9]{8}[A-HJ-NP-TV-Za-hj-np-tv-z]"
    r"|[XYZxyz][0-9]{7}[A-HJ-NP-TV-Za-hj-np-tv-z])\b"
)


class OcrError(Exception):
    pass


class OcrService:
    def extract_national_id(self, content: bytes) -> str:
        """Pre-process image bytes and return the extracted national ID number.

        Raises OcrError if no recognisable ID pattern is found.
        """
        try:
            pil_image = Image.open(io.BytesIO(content)).convert("RGB")
        except Exception as exc:
            raise OcrError("Could not decode image") from exc

        img = np.array(pil_image)
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        kernel = np.ones((1, 1), np.uint8)
        processed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

        raw: str = str(
            pytesseract.image_to_string(  # type: ignore[reportUnknownMemberType]
                processed, lang="spa+eng", config="--psm 6"
            )
        )
        logger.debug("ocr_raw_text", chars=len(raw))

        match = ID_PATTERN.search(raw)
        if not match:
            raise OcrError("Could not extract a national ID number from the document")

        return str(match.group(0)).upper()
