from stash.enrich.ytdlp import YTDLP_OPTIONS


def test_the_option_table_allows_every_default_extractor_except_the_generic_one() -> None:
    # Assert
    assert YTDLP_OPTIONS["allowed_extractors"] == ("default", "-generic")
