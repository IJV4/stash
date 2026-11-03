from pathlib import Path

import pytest

from stash.evaluation.ocr import NoOcr, OcrError


def test_reading_with_no_ocr_available_raises_ocr_error() -> None:
    # Execute / Assert
    with pytest.raises(OcrError, match="OCR is not available"):
        NoOcr().read(Path("images/recipe_card.png"))
