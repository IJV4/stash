from fakes.search_path import FakeSearchPath

from stash.app.ocr import make_ocr
from stash.evaluation import NoOcr
from stash.evaluation.tesseract import TesseractOcr


def test_without_tesseract_on_the_path_there_is_no_ocr() -> None:
    # Execute
    ocr = make_ocr(FakeSearchPath())

    # Assert
    assert isinstance(ocr, NoOcr)


def test_with_tesseract_on_the_path_the_tesseract_adapter_is_used() -> None:
    # Execute
    ocr = make_ocr(FakeSearchPath({"tesseract": "/usr/bin/tesseract"}))

    # Assert
    assert isinstance(ocr, TesseractOcr)
