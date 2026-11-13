import logging
from collections.abc import Sequence
from pathlib import Path

from capture_builders import RAMEN_URL, a_filing_answer, a_message
from capture_narrowing import handle_filed
from capture_rig import build_rig
from link_builders import a_link_info
from log_records import recording_logs

from stash.app.media_files import DirectoryMediaKeeper
from stash.capture import Duplicate, reply_for
from stash.capture.replies import TELEGRAM_TEXT_LIMIT, telegram_length
from stash.domain import CaptureStatus, Stage

TEN_THOUSAND = 10_000
TITLE_LIMIT = 120
PIPELINE_LOGGER = "stash"


class ExplodingKeeper:
    def keep(self, capture_id: str, paths: Sequence[str]) -> tuple[str, ...]:
        raise RuntimeError("disk on fire")


def test_sharing_a_link_replies_with_a_confirmation_and_files_the_item_with_the_link_and_note() -> (
    None
):
    # Setup
    text = f"{RAMEN_URL} try this in March"
    rig = build_rig(
        answer=a_filing_answer(),
        links={RAMEN_URL: a_link_info(url=RAMEN_URL, platform="web")},
    )

    # Execute
    reply = reply_for(handle_filed(rig, a_message(text)))

    # Assert
    [item] = rig.store.list_items()
    assert reply.text == "✅ Places · Tokyo · Want to"
    assert [button.label for row in reply.buttons for button in row] == [
        "Type",
        "Stage",
        "Done ✓",
    ]
    assert item.stage is Stage.WANT_TO
    assert item.source_url == RAMEN_URL
    assert item.note == text


def test_sending_the_same_message_twice_creates_one_item_and_the_second_is_a_duplicate() -> None:
    # Setup
    rig = build_rig(answer=a_filing_answer())
    first = handle_filed(rig, a_message(RAMEN_URL, message_id="m1"))

    # Execute
    second = rig.pipeline.handle(a_message(RAMEN_URL, message_id="m1"))

    # Assert
    assert second == Duplicate()
    assert len(rig.store.list_items()) == 1
    assert rig.store.pending_captures() == []
    first_capture = rig.store.get_capture(first.item.capture_id)
    assert first_capture is not None
    assert first_capture.status is CaptureStatus.FILED


def test_typing_a_thought_replies_with_the_type_and_stage_and_no_detail_segment() -> None:
    # Setup
    rig = build_rig(
        answer=a_filing_answer(item_type="idea", title="Sell candles", details={}),
    )

    # Execute
    result = handle_filed(rig, a_message("idea: sell handmade candles at the weekend market"))

    # Assert
    assert reply_for(result).text == "✅ Ideas · Want to"


def test_a_message_of_ten_thousand_characters_is_saved_whole_with_a_short_title_and_reply() -> None:
    # Setup
    text = ("candle " * 1429)[:TEN_THOUSAND]
    rig = build_rig(answer=a_filing_answer(title="", details={}))

    # Execute
    result = handle_filed(rig, a_message(text))

    # Assert
    assert len(text) == TEN_THOUSAND
    assert result.item.note == text
    assert len(result.item.title) <= TITLE_LIMIT
    assert telegram_length(reply_for(result).text) <= TELEGRAM_TEXT_LIMIT


def test_an_image_with_no_caption_is_saved_untitled_without_asking_the_ai_and_confirmed() -> None:
    # Setup
    rig = build_rig()
    message = a_message("", media_paths=("media/photo-1.jpg",))

    # Execute
    result = handle_filed(rig, message)

    # Assert
    capture = rig.store.get_capture(result.item.capture_id)
    assert capture is not None
    assert capture.media_paths == ("media/photo-1.jpg",)
    assert result.item.title == "Untitled"
    assert rig.model.calls == []
    assert reply_for(result).text == "✅ Other · Inbox"


def test_an_image_is_copied_into_the_data_directory_and_the_capture_points_at_the_copy(
    tmp_path: Path,
) -> None:
    # Setup
    source = tmp_path / "hermes_cache" / "photo.PNG"
    source.parent.mkdir()
    source.write_bytes(b"fake image bytes")
    media_root = tmp_path / "data" / "media"
    rig = build_rig(keeper=DirectoryMediaKeeper(media_root))

    # Execute
    capture = rig.pipeline.receive(a_message("", media_paths=(str(source),)))
    source.unlink()

    # Assert
    assert capture is not None
    stored = rig.store.get_capture(capture.id)
    assert stored is not None
    [kept] = stored.media_paths
    assert kept == str(media_root / f"{capture.id}-0.png")
    assert Path(kept).read_bytes() == b"fake image bytes"


def test_a_missing_image_does_not_stop_the_capture_being_saved(tmp_path: Path) -> None:
    # Setup
    missing = str(tmp_path / "gone.png")
    rig = build_rig(keeper=DirectoryMediaKeeper(tmp_path / "media"))

    # Execute
    with recording_logs(PIPELINE_LOGGER) as recorder:
        capture = rig.pipeline.receive(a_message("", media_paths=(missing,)))
    entries = [entry for entry in recorder.entries() if entry[0] == logging.WARNING]

    # Assert
    assert capture is not None
    assert capture.media_paths == (missing,)
    [(_, warning)] = entries
    assert capture.id in warning
    assert "missing" in warning


def test_a_media_keeper_that_fails_does_not_stop_the_capture_being_saved() -> None:
    # Setup
    rig = build_rig(keeper=ExplodingKeeper())

    # Execute
    capture = rig.pipeline.receive(a_message("", media_paths=("media/photo-1.jpg",)))

    # Assert
    assert capture is not None
    assert capture.media_paths == ("media/photo-1.jpg",)
