import pytest

from stash.domain.media import safe_media_paths


def test_a_bare_string_raises_type_error_naming_the_field() -> None:
    # Execute / Assert
    with pytest.raises(TypeError, match="photos must be a collection of strings"):
        safe_media_paths("photos", "photo.jpg")


@pytest.mark.parametrize(
    ("path", "problem"),
    [
        ("   ", "must not be blank"),
        ("media/a\x00.jpg", "NUL character"),
        ("https://evil.example/a.jpg", "must not be a URL"),
        ("media/../secret.jpg", "'..' segment"),
    ],
)
def test_one_unsafe_path_among_safe_ones_raises_value_error(path: str, problem: str) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match=problem):
        safe_media_paths("media_paths", ["media/a.jpg", path])
