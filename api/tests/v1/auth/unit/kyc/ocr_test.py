"""Unit tests for OcrService — tests the ID extraction logic without Tesseract."""

from unittest.mock import MagicMock, patch

import pytest

from com.qode.qrew.v1.service.services.kyc.ocr import ID_PATTERN, OcrError, OcrService


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("12345678Z", "12345678Z"),
        ("12345678z", "12345678z"),
        ("X1234567Z", "X1234567Z"),
        ("Y2345678A", "Y2345678A"),
        ("Z3456789B", "Z3456789B"),
        ("DNI: 12345678Z issued", "12345678Z"),
    ],
)
def test_id_pattern_matches_valid_ids(text: str, expected: str) -> None:
    match = ID_PATTERN.search(text)
    assert match is not None
    assert match.group(0) == expected


@pytest.mark.parametrize(
    "text",
    [
        "1234567Z",
        "123456789Z",
        "A1234567Z",
        "12345678O",
        "12345678I",
        "12345678U",
        "hello world",
    ],
)
def test_id_pattern_rejects_invalid_ids(text: str) -> None:
    assert ID_PATTERN.search(text) is None


def _make_service() -> OcrService:
    return OcrService()


def test_extract_national_id_returns_uppercased_id() -> None:
    svc = _make_service()

    with (
        patch("com.qode.qrew.v1.service.services.kyc.ocr.Image") as mock_image,
        patch("com.qode.qrew.v1.service.services.kyc.ocr.cv2") as mock_cv2,
        patch("com.qode.qrew.v1.service.services.kyc.ocr.np") as mock_np,
        patch("com.qode.qrew.v1.service.services.kyc.ocr.pytesseract") as mock_tess,
    ):
        mock_image.open.return_value.convert.return_value = MagicMock()
        mock_np.array.return_value = MagicMock()
        mock_cv2.cvtColor.return_value = MagicMock()
        mock_cv2.threshold.return_value = (None, MagicMock())
        mock_np.ones.return_value = MagicMock()
        mock_cv2.morphologyEx.return_value = MagicMock()
        mock_tess.image_to_string.return_value = (
            "Name: GARCIA  ID: 12345678z  Exp: 01/01/2030"
        )

        result = svc.extract_national_id(b"fake-image-bytes")

    assert result == "12345678Z"


def test_extract_national_id_raises_ocr_error_when_no_id_found() -> None:
    svc = _make_service()

    with (
        patch("com.qode.qrew.v1.service.services.kyc.ocr.Image") as mock_image,
        patch("com.qode.qrew.v1.service.services.kyc.ocr.cv2") as mock_cv2,
        patch("com.qode.qrew.v1.service.services.kyc.ocr.np") as mock_np,
        patch("com.qode.qrew.v1.service.services.kyc.ocr.pytesseract") as mock_tess,
    ):
        mock_image.open.return_value.convert.return_value = MagicMock()
        mock_np.array.return_value = MagicMock()
        mock_cv2.cvtColor.return_value = MagicMock()
        mock_cv2.threshold.return_value = (None, MagicMock())
        mock_np.ones.return_value = MagicMock()
        mock_cv2.morphologyEx.return_value = MagicMock()
        mock_tess.image_to_string.return_value = "blurry unreadable text @@#!!"

        with pytest.raises(OcrError, match="Could not extract"):
            svc.extract_national_id(b"bad-image")


def test_extract_national_id_raises_ocr_error_on_invalid_image() -> None:
    svc = _make_service()

    with patch("com.qode.qrew.v1.service.services.kyc.ocr.Image") as mock_image:
        mock_image.open.side_effect = Exception("cannot identify image file")

        with pytest.raises(OcrError, match="Could not decode image"):
            svc.extract_national_id(b"not-an-image")


def test_extract_national_id_extracts_nie() -> None:
    svc = _make_service()

    with (
        patch("com.qode.qrew.v1.service.services.kyc.ocr.Image") as mock_image,
        patch("com.qode.qrew.v1.service.services.kyc.ocr.cv2") as mock_cv2,
        patch("com.qode.qrew.v1.service.services.kyc.ocr.np") as mock_np,
        patch("com.qode.qrew.v1.service.services.kyc.ocr.pytesseract") as mock_tess,
    ):
        mock_image.open.return_value.convert.return_value = MagicMock()
        mock_np.array.return_value = MagicMock()
        mock_cv2.cvtColor.return_value = MagicMock()
        mock_cv2.threshold.return_value = (None, MagicMock())
        mock_np.ones.return_value = MagicMock()
        mock_cv2.morphologyEx.return_value = MagicMock()
        mock_tess.image_to_string.return_value = "Extranjero NIE X1234567Z valid"

        result = svc.extract_national_id(b"nie-image")

    assert result == "X1234567Z"
