from pathlib import Path

import pytest
from eval_builders import a_text_case, an_image_case

from stash.evaluation import CaseKind
from stash.llm import ImagePart


def test_the_case_kinds_are_text_and_image() -> None:
    # Assert
    assert [kind.value for kind in CaseKind] == ["text", "image"]


def test_an_image_case_without_an_image_file_is_rejected() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="image case needs an image"):
        an_image_case(image_path=None)


def test_a_text_case_with_an_image_file_is_rejected() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="text case cannot have an image"):
        a_text_case(image_path=Path("images/a.png"))


def test_a_case_with_a_blank_id_is_rejected() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="id must not be blank"):
        a_text_case(id="  ")


def test_an_image_file_of_an_unsupported_type_is_rejected() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="unsupported image type"):
        an_image_case(image_path=Path("images/scan.tiff"))


def test_an_image_case_names_its_image_file() -> None:
    # Execute
    case = an_image_case(image_path=Path("images/a.png"))

    # Assert
    assert case.image_file() == Path("images/a.png")


def test_a_text_case_has_no_image_file() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="no image"):
        a_text_case().image_file()


def test_png_bytes_become_a_base64_png_data_url() -> None:
    # Setup
    case = an_image_case(image_path=Path("images/a.png"))

    # Execute
    part = case.image_part(b"\x89PNG")

    # Assert
    assert part == ImagePart("data:image/png;base64,iVBORw==")


@pytest.mark.parametrize(
    ("name", "media_type"),
    [
        ("photo.jpg", "image/jpeg"),
        ("photo.JPEG", "image/jpeg"),
        ("shot.webp", "image/webp"),
        ("anim.gif", "image/gif"),
    ],
)
def test_the_media_type_follows_the_file_extension(name: str, media_type: str) -> None:
    # Setup
    case = an_image_case(image_path=Path("images") / name)

    # Execute
    part = case.image_part(b"x")

    # Assert
    assert part.data_url.startswith(f"data:{media_type};base64,")
