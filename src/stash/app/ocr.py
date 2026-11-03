from collections.abc import Callable

from stash.evaluation import NoOcr, Ocr

TESSERACT = "tesseract"


def make_ocr(which: Callable[[str], str | None]) -> Ocr:
    if which(TESSERACT) is None:
        return NoOcr()
    from stash.evaluation.tesseract import TesseractOcr

    return TesseractOcr()
