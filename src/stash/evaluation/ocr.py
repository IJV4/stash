from pathlib import Path
from typing import Protocol


class OcrError(Exception):
    pass


class Ocr(Protocol):
    def read(self, path: Path) -> str: ...


class NoOcr:
    def read(self, path: Path) -> str:
        raise OcrError("OCR is not available")
