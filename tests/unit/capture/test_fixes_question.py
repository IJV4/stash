import pytest
from builders import a_capture
from capture_builders import store_with_filed_item
from capture_rig import a_fix_handler
from fakes.failing_delete_store import DeleteFailed, FailingDeleteStore

from stash.capture import gone
from stash.capture.fixes import Reroute
from stash.domain import CaptureStatus


def test_pressing_that_was_a_question_hands_the_original_text_back_for_rerouting() -> None:
    # Setup
    store, _ = store_with_filed_item()

    # Execute
    answer = a_fix_handler(store).apply("stash:q:c1")

    # Assert
    assert answer == Reroute(a_capture().text)


def test_pressing_that_was_a_question_deletes_the_item() -> None:
    # Setup
    store, _ = store_with_filed_item()

    # Execute
    a_fix_handler(store).apply("stash:q:c1")

    # Assert
    assert store.get_item("c1") is None


def test_pressing_that_was_a_question_marks_the_capture_as_a_request() -> None:
    # Setup
    store, _ = store_with_filed_item()

    # Execute
    a_fix_handler(store).apply("stash:q:c1")

    # Assert
    capture = store.get_capture("c1")
    assert capture is not None and capture.status is CaptureStatus.REQUEST


def test_pressing_that_was_a_question_a_second_time_answers_gone() -> None:
    # Setup
    store, _ = store_with_filed_item()
    handler = a_fix_handler(store)
    handler.apply("stash:q:c1")

    # Execute
    answer = handler.apply("stash:q:c1")

    # Assert
    assert answer == gone()


def test_pressing_that_was_a_question_for_an_unknown_capture_answers_gone() -> None:
    # Setup
    store, _ = store_with_filed_item()

    # Execute
    answer = a_fix_handler(store).apply("stash:q:unknown")

    # Assert
    assert answer == gone()


def test_pressing_that_was_a_question_when_the_item_is_already_deleted_changes_no_status() -> None:
    # Setup
    store, _ = store_with_filed_item()
    store.delete_item("c1")

    # Execute
    a_fix_handler(store).apply("stash:q:c1")

    # Assert
    capture = store.get_capture("c1")
    assert capture is not None and capture.status is CaptureStatus.FILED


def test_a_crash_while_deleting_the_item_leaves_the_capture_already_marked_as_a_request() -> None:
    # Setup
    store, _ = store_with_filed_item(FailingDeleteStore())

    # Execute
    with pytest.raises(DeleteFailed):
        a_fix_handler(store).apply("stash:q:c1")

    # Assert
    capture = store.get_capture("c1")
    assert capture is not None and capture.status is CaptureStatus.REQUEST


def test_pressing_that_was_a_question_for_an_already_marked_request_hands_the_text_back() -> None:
    # Setup
    store, _ = store_with_filed_item()
    store.set_capture_status("c1", CaptureStatus.REQUEST)

    # Execute
    answer = a_fix_handler(store).apply("stash:q:c1")

    # Assert
    assert answer == Reroute(a_capture().text)


def test_pressing_that_was_a_question_for_an_already_marked_request_deletes_the_item() -> None:
    # Setup
    store, _ = store_with_filed_item()
    store.set_capture_status("c1", CaptureStatus.REQUEST)

    # Execute
    a_fix_handler(store).apply("stash:q:c1")

    # Assert
    assert store.get_item("c1") is None


def test_pressing_that_was_a_question_again_after_a_crash_while_deleting_hands_the_text_back() -> (
    None
):
    # Setup
    store, _ = store_with_filed_item(FailingDeleteStore())
    handler = a_fix_handler(store)
    with pytest.raises(DeleteFailed):
        handler.apply("stash:q:c1")

    # Execute
    answer = handler.apply("stash:q:c1")

    # Assert
    assert answer == Reroute(a_capture().text)


def test_pressing_that_was_a_question_again_after_a_crash_while_deleting_deletes_the_item() -> None:
    # Setup
    store, _ = store_with_filed_item(FailingDeleteStore())
    handler = a_fix_handler(store)
    with pytest.raises(DeleteFailed):
        handler.apply("stash:q:c1")

    # Execute
    handler.apply("stash:q:c1")

    # Assert
    assert store.get_item("c1") is None
