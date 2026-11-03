import pytest

from stash.enrich import urls
from stash.enrich.ytdlp import YTDLP_OPTIONS


def test_the_ytdlp_options_cannot_be_changed() -> None:
    # Execute / Assert
    with pytest.raises(TypeError):
        YTDLP_OPTIONS["quiet"] = False  # type: ignore[index]


def test_the_platform_domain_table_cannot_be_changed() -> None:
    # Execute / Assert
    with pytest.raises(TypeError):
        urls._PLATFORM_DOMAINS["evil.example"] = "youtube"


def test_the_bracket_pairs_cannot_be_changed() -> None:
    # Execute / Assert
    with pytest.raises(TypeError):
        urls._OPENER_OF[">"] = "<"
