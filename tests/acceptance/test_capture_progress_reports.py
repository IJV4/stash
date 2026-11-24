from collections.abc import Mapping

from builders import a_capture, a_source, an_item, fetched_item
from capture_builders import (
    a_message,
    an_agent_message,
    an_unsure_answer,
    button_data,
    button_labels,
    text_of,
)
from capture_rig import CaptureRig, build_rig

from stash.capture import Filed, gone, reply_for
from stash.domain import CaptureStatus, Item, Stage
from stash.llm import LlmError, LlmUnavailable

REPORT = "Finished the brisket"
FINISHED = {"says_it_is_finished": True, "item": 1}
NOT_FINISHED = {"says_it_is_finished": False, "item": 0}
MARK_DONE = "Mark done: Smoke a brisket"


def rig_with_open_brisket(*outcomes: Mapping[str, object] | LlmError) -> tuple[CaptureRig, Item]:
    rig = build_rig(outcomes=[an_unsure_answer(title=REPORT), *outcomes], matching=True)
    brisket = an_item(id="b1", capture_id="b1", title="Smoke a brisket", stage=Stage.WANT_TO)
    rig.store.add_capture(a_capture(id="b1", source=a_source("seed"), status=CaptureStatus.FILED))
    rig.store.save_item(brisket)
    return rig, brisket


def filed_report(rig: CaptureRig) -> Filed:
    result = rig.pipeline.handle(a_message(REPORT))
    assert isinstance(result, Filed)
    return result


def test_a_progress_report_offers_to_mark_the_matching_open_item_done() -> None:
    # Setup
    rig, brisket = rig_with_open_brisket(FINISHED)

    # Execute
    filed = filed_report(rig)

    # Assert
    assert filed.finishes == brisket
    assert MARK_DONE in [label for row in button_labels(reply_for(filed).buttons) for label in row]


def test_the_mark_done_button_completes_the_open_item_and_removes_the_stray_one() -> None:
    # Setup
    rig, brisket = rig_with_open_brisket(FINISHED)
    filed = filed_report(rig)
    data = button_data(reply_for(filed), MARK_DONE)

    # Execute
    answer = rig.fixes.apply(data)

    # Assert
    assert text_of(answer).startswith("🎉 Done: Smoke a brisket")
    assert fetched_item(rig.store, brisket.id).stage is Stage.DONE
    assert rig.store.get_item(filed.item.id) is None
    capture = rig.store.get_capture(filed.item.capture_id)
    assert capture is not None and capture.text == REPORT


def test_pressing_mark_done_twice_answers_gone_the_second_time() -> None:
    # Setup
    rig, _ = rig_with_open_brisket(FINISHED)
    data = button_data(reply_for(filed_report(rig)), MARK_DONE)
    rig.fixes.apply(data)

    # Execute
    again = rig.fixes.apply(data)

    # Assert
    assert again == gone()


def test_a_button_naming_no_open_item_changes_nothing() -> None:
    # Setup
    rig, brisket = rig_with_open_brisket(FINISHED)
    filed = filed_report(rig)

    # Execute
    answer = rig.fixes.apply(f"stash:p:{filed.item.id}:nosuchitem")

    # Assert
    assert answer == gone()
    assert rig.store.get_item(filed.item.id) is not None
    assert fetched_item(rig.store, brisket.id).stage is Stage.WANT_TO


def test_a_report_the_model_does_not_tie_to_an_item_is_filed_with_no_button() -> None:
    # Setup
    rig, _ = rig_with_open_brisket(NOT_FINISHED)

    # Execute
    filed = filed_report(rig)

    # Assert
    assert filed.finishes is None
    assert all(
        "Mark done" not in label for row in button_labels(reply_for(filed).buttons) for label in row
    )


def test_a_failing_match_leaves_the_report_filed_as_before() -> None:
    # Setup
    rig, _ = rig_with_open_brisket(LlmUnavailable())

    # Execute
    filed = filed_report(rig)

    # Assert
    assert (filed.finishes, filed.unsure) == (None, True)


def test_a_capture_from_the_agent_is_never_matched() -> None:
    # Setup
    rig, _ = rig_with_open_brisket()
    capture = rig.pipeline.receive(an_agent_message(REPORT))
    assert capture is not None

    # Execute
    result = rig.pipeline.process_agent(capture)

    # Assert
    assert isinstance(result, Filed) and result.finishes is None
