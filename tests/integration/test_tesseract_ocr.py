import shutil
import stat
import struct
import warnings
import zlib
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytesseract
import pytest
from eval_files import SHIPPED_IMAGES
from PIL import Image

from stash.evaluation import OcrError
from stash.evaluation.tesseract import TESSERACT_TIMEOUT_SECONDS, TesseractOcr

RECIPE_CARD = SHIPPED_IMAGES / "recipe_card.png"


@pytest.mark.integration
def test_tesseract_reads_the_title_of_the_shipped_recipe_card() -> None:
    # Setup
    if shutil.which("tesseract") is None:
        pytest.skip("tesseract is not installed")

    # Execute
    text = TesseractOcr().read(RECIPE_CARD)

    # Assert
    assert "Lemon" in text


@pytest.mark.integration
def test_a_missing_image_file_raises_ocr_error(tmp_path: Path) -> None:
    # Execute / Assert
    with pytest.raises(OcrError, match="FileNotFoundError"):
        TesseractOcr().read(tmp_path / "missing.png")


@pytest.mark.integration
def test_a_file_that_is_not_an_image_raises_ocr_error(tmp_path: Path) -> None:
    # Setup
    broken = tmp_path / "broken.png"
    broken.write_bytes(b"this is not a png")

    # Execute / Assert
    with pytest.raises(OcrError, match="UnidentifiedImageError"):
        TesseractOcr().read(broken)


HUGE_SIDE = 20_000
LARGE_SIDE = 10_000


def png_declaring(width: int, height: int) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(b""))
        + chunk(b"IEND", b"")
    )


@contextmanager
def tesseract_command(script: Path) -> Iterator[None]:
    original = pytesseract.pytesseract.tesseract_cmd
    pytesseract.pytesseract.tesseract_cmd = str(script)
    try:
        yield
    finally:
        pytesseract.pytesseract.tesseract_cmd = original


def a_tesseract_that_never_answers(directory: Path) -> Path:
    script = directory / "tesseract"
    script.write_text("#!/bin/sh\nexec sleep 5\n")
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    return script


@pytest.mark.integration
def test_an_image_declaring_a_decompression_bomb_size_raises_ocr_error(tmp_path: Path) -> None:
    # Setup
    bomb = tmp_path / "bomb.png"
    bomb.write_bytes(png_declaring(HUGE_SIDE, HUGE_SIDE))

    # Execute / Assert
    with pytest.raises(OcrError, match="DecompressionBombError"):
        TesseractOcr().read(bomb)


@pytest.mark.integration
def test_an_image_that_only_warns_of_a_decompression_bomb_raises_ocr_error_when_warnings_are_errors(
    tmp_path: Path,
) -> None:
    # Setup
    large = tmp_path / "large.png"
    large.write_bytes(png_declaring(LARGE_SIDE, LARGE_SIDE))

    # Execute / Assert
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        with pytest.raises(OcrError, match="DecompressionBombWarning"):
            TesseractOcr().read(large)


@pytest.mark.integration
def test_a_tesseract_that_outlasts_the_timeout_raises_ocr_error(tmp_path: Path) -> None:
    # Setup
    picture = tmp_path / "picture.png"
    Image.new("RGB", (4, 4)).save(picture)

    # Execute / Assert
    with (
        tesseract_command(a_tesseract_that_never_answers(tmp_path)),
        pytest.raises(OcrError, match="Tesseract process timeout"),
    ):
        TesseractOcr(timeout_seconds=0.2).read(picture)


@pytest.mark.integration
def test_the_default_ocr_timeout_is_thirty_seconds() -> None:
    # Assert
    assert TESSERACT_TIMEOUT_SECONDS == 30
