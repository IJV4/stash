import pytest
from builders import an_outcome, fetched_item, minutes_after
from capture_builders import (
    COMPLETED_ITEM_ID,
    COMPLETED_OUTCOME_ID,
    COMPLETED_TITLE,
    INVALID_KEEP_CHOICES,
    a_store_with_a_completed_item,
    rating_row_data,
    store_with_filed_item,
    text_of,
)
from capture_rig import a_fix_handler
from fakes.memory_store import MemoryStore
from lifecycle_rig import a_lifecycle

from stash.capture import Reply, gone
from stash.capture.completion_replies import kept_reply
from stash.capture.replies import refused
from stash.lifecycle.errors import LifecycleRefused


def test_pressing_keep_answers_the_kept_reply() -> None:
    # Setup
    store = a_store_with_a_completed_item()

    # Execute
    reply = a_fix_handler(store).apply(f"stash:k:{COMPLETED_ITEM_ID}:1")

    # Assert
    assert reply == kept_reply(a_lifecycle(store).history(COMPLETED_ITEM_ID))


def test_pressing_keep_keeps_the_item() -> None:
    # Setup
    store = a_store_with_a_completed_item()

    # Execute
    a_fix_handler(store).apply(f"stash:k:{COMPLETED_ITEM_ID}:1")

    # Assert
    assert fetched_item(store, COMPLETED_ITEM_ID).kept is True


def test_pressing_keep_twice_leaves_the_item_kept_with_the_same_reply() -> None:
    # Setup
    store = a_store_with_a_completed_item()
    handler = a_fix_handler(store)
    first = handler.apply(f"stash:k:{COMPLETED_ITEM_ID}:1")

    # Execute
    second = handler.apply(f"stash:k:{COMPLETED_ITEM_ID}:1")

    # Assert
    assert (second, fetched_item(store, COMPLETED_ITEM_ID).kept) == (first, True)


def test_pressing_not_keeping_answers_that_the_owner_is_not_keeping_the_title() -> None:
    # Setup
    store = a_store_with_a_completed_item(kept=True)

    # Execute
    reply = a_fix_handler(store).apply(f"stash:k:{COMPLETED_ITEM_ID}:0")

    # Assert
    assert text_of(reply) == f"Okay, not keeping {COMPLETED_TITLE}."


def test_pressing_not_keeping_unkeeps_the_item() -> None:
    # Setup
    store = a_store_with_a_completed_item(kept=True)

    # Execute
    a_fix_handler(store).apply(f"stash:k:{COMPLETED_ITEM_ID}:0")

    # Assert
    assert fetched_item(store, COMPLETED_ITEM_ID).kept is False


def test_keeping_an_item_that_is_no_longer_done_is_refused_with_the_lifecycles_message() -> None:
    # Setup
    store, _ = store_with_filed_item()
    with pytest.raises(LifecycleRefused) as refusal:
        a_lifecycle(store).keep("c1", True)

    # Execute
    reply = a_fix_handler(store).apply("stash:k:c1:1")

    # Assert
    assert reply == refused(str(refusal.value))


def test_keeping_an_item_that_is_no_longer_done_leaves_the_item_unchanged() -> None:
    # Setup
    store, item = store_with_filed_item()

    # Execute
    a_fix_handler(store).apply("stash:k:c1:1")

    # Assert
    assert store.get_item("c1") == item


def test_pressing_keep_for_an_unknown_item_answers_gone() -> None:
    # Setup
    store, _ = store_with_filed_item()

    # Execute
    reply = a_fix_handler(store).apply("stash:k:ghost:1")

    # Assert
    assert reply == gone()


@pytest.mark.parametrize("choice", INVALID_KEEP_CHOICES)
def test_an_invalid_keep_choice_answers_gone(choice: str) -> None:
    # Setup
    store = a_store_with_a_completed_item()

    # Execute
    reply = a_fix_handler(store).apply(f"stash:k:{COMPLETED_ITEM_ID}:{choice}")

    # Assert
    assert reply == gone()


@pytest.mark.parametrize("choice", INVALID_KEEP_CHOICES)
def test_an_invalid_keep_choice_changes_nothing(choice: str) -> None:
    # Setup
    store = a_store_with_a_completed_item()
    before = fetched_item(store, COMPLETED_ITEM_ID)

    # Execute
    a_fix_handler(store).apply(f"stash:k:{COMPLETED_ITEM_ID}:{choice}")

    # Assert
    assert fetched_item(store, COMPLETED_ITEM_ID) == before


RATING_ROW = rating_row_data(COMPLETED_OUTCOME_ID)


def an_unrated_store(**item_overrides: object) -> MemoryStore:
    store = a_store_with_a_completed_item(**item_overrides)
    store.save_outcome(an_outcome(id=COMPLETED_OUTCOME_ID, item_id=COMPLETED_ITEM_ID, rating=None))
    return store


def rating_row_of(reply: object) -> list[str]:
    assert isinstance(reply, Reply)
    return [button.data for row in reply.buttons for button in row]


def test_pressing_keep_before_rating_keeps_the_rating_buttons_of_the_latest_outcome() -> None:
    # Setup
    store = an_unrated_store()

    # Execute
    reply = a_fix_handler(store).apply(f"stash:k:{COMPLETED_ITEM_ID}:1")

    # Assert
    assert rating_row_of(reply) == RATING_ROW


def test_pressing_not_keeping_before_rating_keeps_the_rating_buttons_of_the_latest_outcome() -> (
    None
):
    # Setup
    store = an_unrated_store(kept=True)

    # Execute
    reply = a_fix_handler(store).apply(f"stash:k:{COMPLETED_ITEM_ID}:0")

    # Assert
    assert rating_row_of(reply) == RATING_ROW


def test_pressing_keep_after_rating_answers_without_rating_buttons() -> None:
    # Setup
    store = a_store_with_a_completed_item()

    # Execute
    reply = a_fix_handler(store).apply(f"stash:k:{COMPLETED_ITEM_ID}:1")

    # Assert
    assert rating_row_of(reply) == []


def test_pressing_keep_offers_rating_buttons_for_the_most_recently_recorded_of_two_outcomes() -> (
    None
):
    # Setup
    store = an_unrated_store()
    store.add_outcome(
        an_outcome(
            id="o-newer", item_id=COMPLETED_ITEM_ID, rating=None, recorded_at=minutes_after(5)
        )
    )

    # Execute
    reply = a_fix_handler(store).apply(f"stash:k:{COMPLETED_ITEM_ID}:1")

    # Assert
    assert rating_row_of(reply) == rating_row_data("o-newer")
