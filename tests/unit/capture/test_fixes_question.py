import pytest
from builders import a_capture
from capture_builders import store_with_filed_item
from capture_rig import a_fix_handler
from fakes.faulty_store import FaultyStore, StoreFault

from stash.capture.fixes import HISTORY_KEPT, Reroute
from stash.domain import CaptureStatus


def test_a_crash_while_deleting_the_item_leaves_the_capture_already_marked_as_a_request() -> None:
    # Setup
    store, _ = store_with_filed_item(
        FaultyStore(fail_once={"delete_item_if_untouched": StoreFault("c1")})
    )

    # Execute
    with pytest.raises(StoreFault):
        a_fix_handler(store).apply("stash:q:c1")

    # Assert
    capture = store.get_capture("c1")
    assert capture is not None and capture.status is CaptureStatus.REQUEST


def test_pressing_that_was_a_question_again_after_a_crash_while_deleting_hands_the_text_back() -> (
    None
):
    # Setup
    store, _ = store_with_filed_item(
        FaultyStore(fail_once={"delete_item_if_untouched": StoreFault("c1")})
    )
    handler = a_fix_handler(store)
    with pytest.raises(StoreFault):
        handler.apply("stash:q:c1")

    # Execute
    answer = handler.apply("stash:q:c1")

    # Assert
    assert answer == Reroute(a_capture().text)


def test_pressing_that_was_a_question_again_after_a_crash_while_deleting_deletes_the_item() -> None:
    # Setup
    store, _ = store_with_filed_item(
        FaultyStore(fail_once={"delete_item_if_untouched": StoreFault("c1")})
    )
    handler = a_fix_handler(store)
    with pytest.raises(StoreFault):
        handler.apply("stash:q:c1")

    # Execute
    handler.apply("stash:q:c1")

    # Assert
    assert store.get_item("c1") is None


def test_the_refusal_to_reroute_tells_the_owner_how_to_ask_the_question_again() -> None:
    # Assert
    assert HISTORY_KEPT == (
        "That item has a history now, so I kept it — "
        "send the question again starting with ? to ask."
    )
