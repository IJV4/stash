import sys

import pytest
from fakes.search_path import FakeSearchPath

from stash.app.ocr import make_ocr
from stash.evaluation import NoOcr
from stash.evaluation.tesseract import TesseractOcr


def test_with_tesseract_on_the_path_the_tesseract_adapter_is_used() -> None:
    # Execute
    ocr = make_ocr(FakeSearchPath({"tesseract": "/usr/bin/tesseract"}))

    # Assert
    assert isinstance(ocr, TesseractOcr)


def test_with_the_binary_but_without_the_ocr_extra_there_is_no_ocr(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Setup
    monkeypatch.setitem(sys.modules, "stash.evaluation.tesseract", None)

    # Execute
    ocr = make_ocr(FakeSearchPath({"tesseract": "/usr/bin/tesseract"}))

    # Assert
    assert isinstance(ocr, NoOcr)
