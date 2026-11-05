import pytest
from capture_builders import store_with_filed_item
from capture_rig import a_fix_handler

from stash.capture import gone, stage_menu, type_menu


def test_the_type_button_opens_the_type_menu_for_the_item() -> None:
    # Setup
    store, item = store_with_filed_item()

    # Execute
    reply = a_fix_handler(store).apply("stash:t:c1")

    # Assert
    assert reply == type_menu(item)


def test_the_stage_button_opens_the_stage_menu_for_the_item() -> None:
    # Setup
    store, item = store_with_filed_item()

    # Execute
    reply = a_fix_handler(store).apply("stash:s:c1")

    # Assert
    assert reply == stage_menu(item)


@pytest.mark.parametrize("data", ["stash:t:unknown", "stash:s:unknown"])
def test_a_menu_button_for_an_unknown_item_answers_gone(data: str) -> None:
    # Setup
    store, _ = store_with_filed_item()

    # Execute
    reply = a_fix_handler(store).apply(data)

    # Assert
    assert reply == gone()


@pytest.mark.parametrize(
    "data",
    [
        "",
        "garbage",
        "stash:zz",
        "stash",
        "stash:t:",
        "stash:t:c1:extra",
        "stash:T:c1",
        "stash:q:",
        "\x00",
        "stash:t:" + "é" * 10_000,
        "stash:T:c1:" + "x" * 10_000,
    ],
)
def test_malformed_or_forged_button_data_answers_gone_and_never_raises(data: str) -> None:
    # Setup
    store, _ = store_with_filed_item()

    # Execute
    reply = a_fix_handler(store).apply(data)

    # Assert
    assert reply == gone()
