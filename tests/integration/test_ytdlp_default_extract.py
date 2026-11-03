import subprocess
import sys
from pathlib import Path

import pytest
import yt_dlp
from yt_dlp.utils import YoutubeDLError

from stash.enrich.ytdlp import default_ytdlp_extract, ytdlp_params

LOCAL_PAGE = (
    "<html><head><title>Local page</title></head>"
    '<body><video src="https://example.invalid/clip.mp4"></video></body></html>'
)
IMPORT_THEN_REPORT = "import sys; import stash.enrich.ytdlp; print('yt_dlp' in sys.modules)"


@pytest.mark.integration
def test_the_default_extractor_refuses_a_local_file_url_without_touching_the_network() -> None:
    # Execute / Assert
    with pytest.raises(YoutubeDLError):
        default_ytdlp_extract("file:///etc/hostname")


@pytest.mark.integration
def test_the_default_extractor_refuses_a_local_file_url_even_when_the_file_exists(
    tmp_path: Path,
) -> None:
    # Setup
    page = tmp_path / "page.html"
    page.write_text(LOCAL_PAGE)

    # Execute / Assert
    with pytest.raises(YoutubeDLError):
        default_ytdlp_extract(page.as_uri())


@pytest.mark.integration
def test_importing_the_ytdlp_adapter_does_not_load_yt_dlp() -> None:
    # Execute
    result = subprocess.run(
        [sys.executable, "-I", "-c", IMPORT_THEN_REPORT],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )

    # Assert
    assert result.stdout.strip() == "False"


def matching_extractors(url: str) -> list[str]:
    with yt_dlp.YoutubeDL(ytdlp_params()) as ydl:
        return [key for key, extractor in ydl._ies.items() if extractor.suitable(url)]


@pytest.mark.integration
def test_no_yt_dlp_extractor_accepts_a_plain_web_page() -> None:
    # Execute
    matching = matching_extractors("https://example.com/ramen-tokyo")

    # Assert
    assert matching == []


@pytest.mark.integration
def test_a_youtube_link_is_still_accepted_by_a_yt_dlp_extractor() -> None:
    # Execute
    matching = matching_extractors("https://www.youtube.com/watch?v=abcdefghijk")

    # Assert
    assert "Youtube" in matching


@pytest.mark.integration
def test_the_default_extractor_refuses_a_plain_web_page_because_no_extractor_accepts_it() -> None:
    # Execute / Assert
    with pytest.raises(YoutubeDLError, match="No suitable extractor"):
        default_ytdlp_extract("https://example.com/ramen-tokyo")
