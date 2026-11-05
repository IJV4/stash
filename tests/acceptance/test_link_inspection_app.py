from pathlib import Path

from capture_builders import a_filing_answer, a_message
from cli_rig import CliRig, build_cli_rig
from fakes.hanging_extract import HangingExtract
from fakes.recording_extract import RecordingExtract

from stash.app import StashApp, build_app
from stash.capture import Filed
from stash.config.loader import load_config

VIDEO_URL = "https://www.youtube.com/watch?v=abc123"
PAGE_URL = "https://example.com/ramen-tokyo"
PAGE = "<html><head><title>Ramen Tokyo</title></head></html>"
SHORT_DEADLINE_SECONDS = 0.005
CHAT_PATH = "/v1/chat/completions"


def app_with(rig: CliRig, **overrides: object) -> StashApp:
    return build_app(
        load_config(rig.config_file, rig.env),
        **{
            "client": rig.providers.client(),
            "run": rig.smi,
            "which": rig.search_path,
            "clock": lambda: rig.now,
            **overrides,
        },  # type: ignore[arg-type]
    )


def prompt_sent_to_the_model(rig: CliRig) -> str:
    return rig.providers.sent_to(CHAT_PATH)[0].content.decode()


def test_a_web_link_sent_to_the_app_is_read_by_the_page_reader_and_never_offered_to_yt_dlp(
    tmp_path: Path,
) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    rig.providers.pages[PAGE_URL] = PAGE
    extract = RecordingExtract()
    app = app_with(rig, extract=extract)

    # Execute
    app.pipeline.handle(a_message(PAGE_URL, received_at=rig.now))

    # Assert
    assert (extract.asked, "title: Ramen Tokyo" in prompt_sent_to_the_model(rig)) == ([], True)
    app.close()


def test_a_youtube_link_sent_to_the_app_is_described_by_yt_dlp(tmp_path: Path) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    extract = RecordingExtract()
    app = app_with(rig, extract=extract)

    # Execute
    app.pipeline.handle(a_message(VIDEO_URL, received_at=rig.now))

    # Assert
    assert (extract.asked, "title: Ramen crawl" in prompt_sent_to_the_model(rig)) == (
        [VIDEO_URL],
        True,
    )
    app.close()


def test_a_link_whose_extractor_hangs_is_filed_from_the_owners_own_words_within_the_deadline(
    tmp_path: Path,
) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    extract = HangingExtract()
    app = app_with(rig, extract=extract, inspection_deadline_seconds=SHORT_DEADLINE_SECONDS)

    # Execute
    result = app.pipeline.handle(a_message(f"{VIDEO_URL} try this in March", received_at=rig.now))
    extract.release.set()

    # Assert
    assert (type(result), "title: unknown" in prompt_sent_to_the_model(rig)) == (Filed, True)
    app.close()


def test_a_youtube_links_title_uploader_and_duration_are_saved_on_the_item_over_the_models_own(
    tmp_path: Path,
) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    rig.providers.answer = a_filing_answer(details={"uploader": "someone else"})
    extract = RecordingExtract("Knife skills 101", uploader="Test Kitchen", duration=754.0)
    app = app_with(rig, extract=extract)

    # Execute
    result = app.pipeline.handle(a_message(VIDEO_URL, received_at=rig.now))

    # Assert
    assert isinstance(result, Filed)
    saved = app.store.get_item(result.item.capture_id)
    assert saved is not None and dict(saved.details) == {
        "link_title": "Knife skills 101",
        "uploader": "Test Kitchen",
        "duration": "12:34",
    }
    app.close()
