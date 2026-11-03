from stash.enrich.ytdlp import YTDLP_OPTIONS, ytdlp_params


def test_the_option_table_allows_every_default_extractor_except_the_generic_one() -> None:
    # Assert
    assert YTDLP_OPTIONS["allowed_extractors"] == ("default", "-generic")


def test_the_params_hand_yt_dlp_the_extractor_names_as_a_list() -> None:
    # Execute
    params = ytdlp_params()

    # Assert
    assert params["allowed_extractors"] == ["default", "-generic"]


def test_changing_the_params_of_one_call_leaves_the_next_call_untouched() -> None:
    # Setup
    first = ytdlp_params()
    first["allowed_extractors"].append("generic")  # type: ignore[attr-defined]

    # Execute
    second = ytdlp_params()

    # Assert
    assert second["allowed_extractors"] == ["default", "-generic"]


def test_the_params_are_the_option_table_with_the_extractor_names_as_a_list() -> None:
    # Execute
    params = ytdlp_params()

    # Assert
    assert params == {**YTDLP_OPTIONS, "allowed_extractors": ["default", "-generic"]}
