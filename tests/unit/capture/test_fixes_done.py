from capture_builders import (
    store_with_filed_item,
)
from capture_rig import a_fix_handler

from stash.capture import gone


def test_pressing_done_for_an_unknown_item_answers_gone() -> None:
    # Setup
    store, _ = store_with_filed_item()

    # Execute
    reply = a_fix_handler(store).apply("stash:d:ghost")

    # Assert
    assert reply == gone()
