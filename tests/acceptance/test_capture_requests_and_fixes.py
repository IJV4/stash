from capture_builders import (
    FORCED_QUESTION,
    QUESTION,
    RAMEN_URL,
    a_filing_answer,
    a_message,
    a_request_answer,
    an_unsure_answer,
    button_data,
)
from capture_rig import build_rig
from link_builders import a_link_info

from stash.capture import Filed, IsRequest, Reroute, gone, reply_for
from stash.domain import CaptureStatus, ItemType


def test_a_question_creates_no_item_and_is_marked_as_a_request_for_the_assistant() -> None:
    # Setup
    rig = build_rig(answer=a_request_answer())

    # Execute
    result = rig.pipeline.handle(a_message(QUESTION))
    assert isinstance(result, IsRequest)

    # Assert
    stored = rig.store.get_capture(result.capture.id)
    assert stored is not None
    assert (rig.store.list_items(), stored.status, result.capture.text) == (
        [],
        CaptureStatus.REQUEST,
        QUESTION,
    )


def test_a_message_starting_with_a_question_mark_is_handled_as_a_request_without_the_ai() -> None:
    # Setup
    rig = build_rig(answer=a_filing_answer())

    # Execute
    result = rig.pipeline.handle(a_message(FORCED_QUESTION))

    # Assert
    assert (type(result), rig.model.calls, rig.store.list_items(), rig.inspector.inspected) == (
        IsRequest,
        [],
        [],
        [],
    )


def test_an_unsure_ai_files_the_item_and_the_question_button_reroutes_it_exactly_once() -> None:
    # Setup
    rig = build_rig(answer=an_unsure_answer())
    result = rig.pipeline.handle(a_message(QUESTION))
    assert isinstance(result, Filed)
    reply = reply_for(result)
    data = button_data(reply, "That was a question →")

    # Execute
    first = rig.fixes.apply(data)
    second = rig.fixes.apply(data)

    # Assert
    stored = rig.store.get_capture(result.item.capture_id)
    assert stored is not None
    assert (first, rig.store.list_items(), stored.status, second) == (
        Reroute(QUESTION),
        [],
        CaptureStatus.REQUEST,
        gone(),
    )


def test_choosing_recipes_from_the_type_menu_retypes_the_item_and_shows_the_confirmation() -> None:
    # Setup
    rig = build_rig(
        answer=a_filing_answer(),
        links={RAMEN_URL: a_link_info(url=RAMEN_URL, platform="web")},
    )
    result = rig.pipeline.handle(a_message(RAMEN_URL))
    assert isinstance(result, Filed)
    menu = rig.fixes.apply(button_data(reply_for(result), "Type"))
    assert not isinstance(menu, Reroute)

    # Execute
    reply = rig.fixes.apply(button_data(menu, "Recipes"))
    assert not isinstance(reply, Reroute)

    # Assert
    [item] = rig.store.list_items()
    assert (reply.text, item.item_type) == ("✅ Recipes · Tokyo · Want to", ItemType.RECIPE)


def test_a_stale_or_forged_button_answers_that_the_item_no_longer_exists_and_never_fails() -> None:
    # Setup
    rig = build_rig()
    unknown_item = "stash:t:" + "f" * 32

    # Execute
    answers = [rig.fixes.apply(data) for data in (unknown_item, "garbage", "stash:zz", "")]

    # Assert
    assert answers == [gone()] * 4
