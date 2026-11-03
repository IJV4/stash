import logging
from collections.abc import Mapping

import pytest
from link_builders import VIDEO_URL, a_link_info
from yt_dlp.utils import DownloadError

from stash.enrich.links import LinkInfo
from stash.enrich.ytdlp import YtDlpInspector, info_to_link

FULL_INFO: Mapping[str, object] = {
    "title": "Ramen crawl",
    "description": "Five bowls in one night",
    "uploader": "Hana Eats",
    "duration": 61,
    "subtitles": {"en": [{"ext": "vtt"}]},
}


def test_a_full_info_dict_maps_to_every_link_info_field() -> None:
    # Execute / Assert
    assert info_to_link(VIDEO_URL, FULL_INFO) == a_link_info()


def test_an_empty_info_dict_maps_to_an_unknown_link() -> None:
    # Execute / Assert
    assert info_to_link(VIDEO_URL, {}) == LinkInfo.unknown(VIDEO_URL)


@pytest.mark.parametrize(
    ("duration", "seconds"), [(61.5, 61), (61, 61), (0, 0), (0.9, 0), (3600.0, 3600)]
)
def test_a_numeric_duration_is_truncated_to_whole_seconds(duration: object, seconds: int) -> None:
    # Execute / Assert
    assert info_to_link(VIDEO_URL, {"duration": duration}).duration_s == seconds


@pytest.mark.parametrize(
    "duration",
    [None, "61", True, -1, -0.5, float("nan"), float("inf"), [61], {"s": 61}],
    ids=["none", "string", "bool", "negative-int", "negative-float", "nan", "inf", "list", "dict"],
)
def test_a_duration_that_is_not_a_finite_non_negative_number_is_dropped(duration: object) -> None:
    # Execute / Assert
    assert info_to_link(VIDEO_URL, {"duration": duration}).duration_s is None


def test_the_uploader_is_used_when_present() -> None:
    # Execute / Assert
    info = info_to_link(VIDEO_URL, {"uploader": "Hana Eats", "channel": "Other"})
    assert info.uploader == "Hana Eats"


def test_the_channel_stands_in_when_there_is_no_uploader() -> None:
    # Execute / Assert
    assert info_to_link(VIDEO_URL, {"channel": "Hana Channel"}).uploader == "Hana Channel"


def test_the_channel_stands_in_when_the_uploader_is_not_text() -> None:
    # Execute / Assert
    assert info_to_link(VIDEO_URL, {"uploader": 7, "channel": "Hana Channel"}).uploader == (
        "Hana Channel"
    )


@pytest.mark.parametrize("field", ["title", "description", "uploader"])
def test_a_text_field_that_is_not_text_is_dropped(field: str) -> None:
    # Execute
    info = info_to_link(VIDEO_URL, {field: ["not", "text"]})

    # Assert
    assert getattr(info, field) is None


@pytest.mark.parametrize(
    ("info", "has_captions"),
    [
        ({"subtitles": {"en": [{"ext": "vtt"}]}}, True),
        ({"automatic_captions": {"en": [{"ext": "vtt"}]}}, True),
        ({"subtitles": {}, "automatic_captions": {}}, False),
        ({"subtitles": {}, "automatic_captions": {"en": []}}, True),
        ({"subtitles": ["en"]}, False),
        ({"subtitles": None}, False),
        ({}, False),
    ],
    ids=["manual", "automatic", "both-empty", "automatic-only", "wrong-shape", "none", "absent"],
)
def test_captions_exist_when_manual_or_automatic_captions_are_non_empty(
    info: Mapping[str, object], has_captions: bool
) -> None:
    # Execute / Assert
    assert info_to_link(VIDEO_URL, info).has_captions is has_captions


def test_a_link_info_from_yt_dlp_carries_the_platform_of_the_host() -> None:
    # Execute / Assert
    assert info_to_link("https://youtu.be/abc", FULL_INFO).platform == "youtube"


def test_the_inspector_describes_a_link_from_what_the_extractor_returns() -> None:
    # Setup
    inspector = YtDlpInspector(lambda url: FULL_INFO)

    # Execute / Assert
    assert inspector.inspect(VIDEO_URL) == a_link_info()


def test_the_inspector_hands_the_extractor_the_url_it_was_asked_about() -> None:
    # Setup
    asked: list[str] = []

    def extract(url: str) -> Mapping[str, object]:
        asked.append(url)
        return {}

    # Execute
    YtDlpInspector(extract).inspect(VIDEO_URL)

    # Assert
    assert asked == [VIDEO_URL]


def failing(error: Exception) -> YtDlpInspector:
    def extract(url: str) -> Mapping[str, object]:
        raise error

    return YtDlpInspector(extract)


@pytest.mark.parametrize(
    "error",
    [DownloadError("unsupported URL"), RuntimeError("boom"), KeyError("title"), OSError("disk")],
    ids=["download-error", "runtime-error", "key-error", "os-error"],
)
def test_an_extractor_that_raises_yields_an_unknown_link(error: Exception) -> None:
    # Execute / Assert
    assert failing(error).inspect(VIDEO_URL) == LinkInfo.unknown(VIDEO_URL)


def test_a_failed_extraction_is_logged_as_a_warning_naming_only_the_error_class(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Execute
    failing(DownloadError("secret-token-in-message")).inspect(f"{VIDEO_URL}&sig=hidden")

    # Assert
    assert [(r.levelno, r.getMessage()) for r in caplog.records] == [
        (logging.WARNING, "yt-dlp extraction failed: DownloadError")
    ]


@pytest.mark.parametrize(
    "url", ["http://localhost/a", "http://10.0.0.5/a", "http://192.168.1.1:8080/a"]
)
def test_the_extractor_is_never_asked_about_a_link_that_is_not_public(url: str) -> None:
    # Setup
    asked: list[str] = []

    def extract(candidate: str) -> Mapping[str, object]:
        asked.append(candidate)
        return FULL_INFO

    # Execute
    YtDlpInspector(extract).inspect(url)

    # Assert
    assert asked == []


def test_a_link_that_is_not_public_is_unknown() -> None:
    # Execute / Assert
    assert YtDlpInspector(lambda url: FULL_INFO).inspect("http://10.0.0.5/a") == LinkInfo.unknown(
        "http://10.0.0.5/a"
    )
