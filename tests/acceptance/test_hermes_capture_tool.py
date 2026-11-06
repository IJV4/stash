from capture_builders import FORCED_QUESTION, a_filing_answer, a_request_answer
from capture_rig import CaptureRig, build_rig
from fakes.raising_intake import RaisingIntake
from hermes_registration_rig import OpenedApps, register_stash, register_stash_over
from hermes_rig import app_over
from tool_rig import calling

from stash.domain import Stage
from stash.llm import LlmUnavailable

BOOK = "Tidewater Notes, a novel"
FIVE_STARS = 5


def a_book_answer() -> dict[str, object]:
    return a_filing_answer(item_type="book", title="Tidewater Notes", stage="want_to")


def test_an_unsaved_book_the_owner_finished_is_captured_then_completed_through_the_tools() -> None:
    # Setup
    rig = build_rig(answer=a_book_answer())
    tools = register_stash(app_over(rig)).ctx.tools
    assert calling(tools, "stash_search", {"query": "tidewater"}) == {"items": []}

    # Execute
    captured = calling(tools, "stash_capture", {"text": BOOK})
    calling(tools, "stash_complete", {"item_id": captured["item_id"], "rating": FIVE_STARS})

    # Assert
    item = rig.store.get_item(captured["item_id"])
    assert item is not None and item.stage is Stage.DONE
    assert [outcome.rating for outcome in rig.store.outcomes_for(item.id)] == [FIVE_STARS]


def test_a_capture_made_while_the_ai_is_unavailable_is_saved_pending_with_no_item() -> None:
    # Setup
    rig = build_rig(error=LlmUnavailable("down"))
    tools = register_stash(app_over(rig)).ctx.tools

    # Execute
    answer = calling(tools, "stash_capture", {"text": BOOK})

    # Assert
    assert (
        answer,
        [(capture.text, capture.source.is_agent) for capture in rig.store.pending_captures()],
        rig.store.list_items(),
    ) == ({"saved": True, "pending": True}, [(BOOK, True)], [])


def test_a_capture_starting_with_a_question_mark_is_filed_as_an_item() -> None:
    # Setup
    rig = build_rig(answer=a_book_answer())
    tools = register_stash(app_over(rig)).ctx.tools

    # Execute
    answer = calling(tools, "stash_capture", {"text": FORCED_QUESTION})

    # Assert
    assert rig.store.get_item(answer["item_id"]) is not None


def test_a_capture_the_ai_answers_as_a_request_is_filed_as_an_item() -> None:
    # Setup
    rig = build_rig(answer=a_request_answer())
    tools = register_stash(app_over(rig)).ctx.tools

    # Execute
    answer = calling(tools, "stash_capture", {"text": BOOK})

    # Assert
    assert rig.store.get_item(answer["item_id"]) is not None


def test_the_capture_tool_still_works_after_the_plugin_is_registered_again() -> None:
    # Setup
    rig: CaptureRig = build_rig(answer=a_book_answer())
    plugin = register_stash_over(OpenedApps(rig))
    reloaded = plugin.reloaded().ctx

    # Execute
    answer = calling(reloaded.tools, "stash_capture", {"text": BOOK})

    # Assert
    assert answer["title"] == "Tidewater Notes"


def test_a_capture_whose_filing_fails_unexpectedly_answers_saved_and_pending() -> None:
    # Setup
    rig = build_rig(answer=a_book_answer())
    failing = app_over(rig, lambda inner: RaisingIntake(inner, on_process=RuntimeError("boom")))
    tools = register_stash(failing).ctx.tools

    # Execute
    answer = calling(tools, "stash_capture", {"text": BOOK})

    # Assert
    assert (answer, [capture.text for capture in rig.store.pending_captures()]) == (
        {"saved": True, "pending": True},
        [BOOK],
    )
