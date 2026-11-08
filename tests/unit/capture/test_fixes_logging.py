import logging

import pytest
from builders import stored_completion
from capture_builders import (
    COMPLETED_ITEM_ID,
    COMPLETED_OUTCOME_ID,
    INVALID_KEEP_CHOICES,
    INVALID_RATINGS,
    store_with_filed_item,
)
from capture_rig import logged_by_applying
from fakes.faulty_store import FaultyStore

from stash.capture.callback_log import MAX_LOGGED_CALLBACK_CHARS
from stash.store import UnknownItemError

FORGED = "g" * 500
CLAMPED_CALLBACKS_AND_MESSAGES = [
    ("{}", "unparseable fix callback: {!r}"),
    ("stash:t:{}", "fix callback for unknown item {}"),
    ("stash:s:{}", "fix callback for unknown item {}"),
    ("stash:d:{}", "fix callback for unknown item {}"),
    ("stash:k:{}:1", "fix callback for unknown item {}"),
    ("stash:q:{}", "fix callback for unknown capture {}"),
    ("stash:r:{}:3", "fix callback for unknown outcome {}"),
    ("stash:T:c1:{}", "fix callback for item c1 has an invalid ItemType {!r}"),
    ("stash:S:c1:{}", "fix callback for item c1 has an invalid Stage {!r}"),
    ("stash:r:o1:{}", "fix callback for outcome o1 has an invalid rating {!r}"),
    ("stash:k:i1:{}", "fix callback for item i1 has an invalid KeepChoice {!r}"),
]


@pytest.mark.parametrize("data", ["garbage", "stash:zz:c1", "stash:t:c1:extra", "stash:T:c1"])
def test_callback_data_that_does_not_parse_is_logged_at_warning(data: str) -> None:
    # Setup
    store, _ = store_with_filed_item()

    # Execute / Assert
    assert logged_by_applying(store, data) == [
        (logging.WARNING, f"unparseable fix callback: {data!r}")
    ]


@pytest.mark.parametrize("data", ["stash:t:ghost", "stash:s:ghost", "stash:T:ghost:recipe"])
def test_a_callback_for_an_unknown_item_is_logged_at_info(data: str) -> None:
    # Setup
    store, _ = store_with_filed_item()

    # Execute / Assert
    assert logged_by_applying(store, data) == [
        (logging.INFO, "fix callback for unknown item ghost")
    ]


@pytest.mark.parametrize("data", ["stash:d:ghost", "stash:k:ghost:1", "stash:k:ghost:0"])
def test_a_completion_press_for_an_unknown_item_is_logged_at_info(data: str) -> None:
    # Setup
    store, _ = store_with_filed_item()

    # Execute / Assert
    assert logged_by_applying(store, data) == [
        (logging.INFO, "fix callback for unknown item ghost")
    ]


def test_a_rating_for_an_unknown_outcome_is_logged_at_info() -> None:
    # Setup
    store, _ = store_with_filed_item()

    # Execute / Assert
    assert logged_by_applying(store, "stash:r:ghost:3") == [
        (logging.INFO, "fix callback for unknown outcome ghost")
    ]


def test_a_rating_whose_item_was_deleted_right_after_saving_it_is_logged_at_info() -> None:
    # Setup
    store = FaultyStore()
    stored_completion(store, COMPLETED_ITEM_ID)
    store.fail_next("save_outcome", UnknownItemError(COMPLETED_ITEM_ID))

    # Execute / Assert
    assert logged_by_applying(store, f"stash:r:{COMPLETED_OUTCOME_ID}:3") == [
        (logging.INFO, f"fix callback for unknown item {COMPLETED_ITEM_ID}")
    ]


def test_a_type_that_does_not_exist_is_logged_at_warning() -> None:
    # Setup
    store, _ = store_with_filed_item()

    # Execute / Assert
    assert logged_by_applying(store, "stash:T:c1:spaceship") == [
        (logging.WARNING, "fix callback for item c1 has an invalid ItemType 'spaceship'")
    ]


def test_a_stage_that_does_not_exist_is_logged_at_warning() -> None:
    # Setup
    store, _ = store_with_filed_item()

    # Execute / Assert
    assert logged_by_applying(store, "stash:S:c1:limbo") == [
        (logging.WARNING, "fix callback for item c1 has an invalid Stage 'limbo'")
    ]


@pytest.mark.parametrize("argument", INVALID_RATINGS)
def test_a_rating_that_does_not_exist_is_logged_at_warning(argument: str) -> None:
    # Setup
    store, _ = store_with_filed_item()

    # Execute / Assert
    assert logged_by_applying(store, f"stash:r:o1:{argument}") == [
        (logging.WARNING, f"fix callback for outcome o1 has an invalid rating {argument!r}")
    ]


@pytest.mark.parametrize("choice", INVALID_KEEP_CHOICES)
def test_a_keep_choice_that_does_not_exist_is_logged_at_warning(choice: str) -> None:
    # Setup
    store, _ = store_with_filed_item()

    # Execute / Assert
    assert logged_by_applying(store, f"stash:k:i1:{choice}") == [
        (logging.WARNING, f"fix callback for item i1 has an invalid KeepChoice {choice!r}")
    ]


@pytest.mark.parametrize(("template", "message"), CLAMPED_CALLBACKS_AND_MESSAGES)
def test_a_forged_value_is_logged_cut_to_its_first_64_characters(
    template: str, message: str
) -> None:
    # Setup
    store, _ = store_with_filed_item()
    clamped = FORGED[:MAX_LOGGED_CALLBACK_CHARS]

    # Execute
    entries = logged_by_applying(store, template.format(FORGED))

    # Assert
    assert [text for _, text in entries] == [message.format(clamped)]
