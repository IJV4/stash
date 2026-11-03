from pathlib import Path

import pytesseract
from PIL import Image

from stash.domain import describe_failure
from stash.evaluation.ocr import OcrError

TESSERACT_TIMEOUT_SECONDS = 30

_FAILURES = (
    pytesseract.TesseractError,
    RuntimeError,
    Image.DecompressionBombError,
    Image.DecompressionBombWarning,
    OSError,
)


class TesseractOcr:
    def __init__(self, timeout_seconds: float = TESSERACT_TIMEOUT_SECONDS) -> None:
        self._timeout_seconds = timeout_seconds

    def read(self, path: Path) -> str:
        try:
            with Image.open(path) as image:
                return str(pytesseract.image_to_string(image, timeout=self._timeout_seconds))
        except _FAILURES as failure:
            raise OcrError(describe_failure(failure)) from failure
