from pathlib import Path

from stash.evaluation.ocr import OcrError


class FakeOcr:
    def __init__(self, text: str = "", error: OcrError | None = None) -> None:
        self._text = text
        self._error = error
        self.paths: list[Path] = []

    def read(self, path: Path) -> str:
        self.paths.append(path)
        if self._error is not None:
            raise self._error
        return self._text
