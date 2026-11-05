import datetime as dt

from builders import HEX_ID
from capture_builders import a_placed_item, button_labels

from stash.capture.callbacks import TELEGRAM_CALLBACK_LIMIT
from stash.capture.menus import stage_menu, type_menu
from stash.capture.replies import Reply, confirmation
from stash.domain import ItemType, Stage

A_DATE = dt.date(2026, 11, 14)


def _offered(reply: Reply) -> list[Stage]:
    return [
        Stage(button.data.split(":")[3])
        for row in reply.buttons
        for button in row
        if button.data.startswith("stash:S:")
    ]


def test_the_type_menu_asks_the_owner_to_pick_a_type() -> None:
    # Execute
    reply = type_menu(a_placed_item())

    # Assert
    assert reply.text == "Pick a type:"


def test_the_type_menu_has_one_button_per_item_type_in_rows_of_three() -> None:
    # Execute
    reply = type_menu(a_placed_item())

    # Assert
    assert button_labels(reply.buttons) == [
        ["Places", "Recipes", "Purchases"],
        ["Learning", "Books", "Media"],
        ["Ideas", "Plans", "Activities"],
        ["Gifts", "Other"],
    ]


def test_each_type_button_carries_the_item_id_and_its_type_value() -> None:
    # Execute
    reply = type_menu(a_placed_item(id="i7"))

    # Assert
    assert [button.data for row in reply.buttons for button in row] == [
        f"stash:T:i7:{item_type.value}" for item_type in ItemType
    ]


def test_an_item_without_a_date_is_offered_inbox_want_to_doing_and_dropped() -> None:
    # Execute
    reply = stage_menu(a_placed_item(id="i7", date=None))

    # Assert
    assert _offered(reply) == [Stage.INBOX, Stage.WANT_TO, Stage.DOING, Stage.DROPPED]


def test_an_item_with_a_date_is_also_offered_planned() -> None:
    # Execute
    reply = stage_menu(a_placed_item(id="i7", date=A_DATE))

    # Assert
    assert _offered(reply) == [
        Stage.INBOX,
        Stage.WANT_TO,
        Stage.PLANNED,
        Stage.DOING,
        Stage.DROPPED,
    ]


def test_the_stage_menu_asks_the_owner_to_pick_a_stage() -> None:
    # Execute
    reply = stage_menu(a_placed_item())

    # Assert
    assert reply.text == "Pick a stage:"


def test_the_stage_menu_for_a_dateless_item_has_two_rows_of_two_then_a_done_row() -> None:
    # Execute
    reply = stage_menu(a_placed_item(date=None))

    # Assert
    assert button_labels(reply.buttons) == [["Inbox", "Want to"], ["Doing", "Dropped"], ["Done ✓"]]


def test_the_stage_menu_for_a_dated_item_has_a_short_stage_row_then_a_done_row() -> None:
    # Execute
    reply = stage_menu(a_placed_item(date=A_DATE))

    # Assert
    assert button_labels(reply.buttons) == [
        ["Inbox", "Want to"],
        ["Planned", "Doing"],
        ["Dropped"],
        ["Done ✓"],
    ]


def test_each_stage_button_carries_the_item_id_and_its_stage_value() -> None:
    # Execute
    reply = stage_menu(a_placed_item(id="i7", date=A_DATE))

    # Assert
    assert [
        button.data for row in reply.buttons for button in row if button.data.startswith("stash:S:")
    ] == [
        "stash:S:i7:inbox",
        "stash:S:i7:want_to",
        "stash:S:i7:planned",
        "stash:S:i7:doing",
        "stash:S:i7:dropped",
    ]


def test_every_button_of_every_kind_for_32_hex_ids_fits_the_telegram_limit() -> None:
    # Setup
    item = a_placed_item(id=HEX_ID, capture_id=HEX_ID, date=A_DATE)
    replies = [type_menu(item), stage_menu(item), confirmation(item, unsure=True)]

    # Execute
    longest = max(
        len(button.data.encode("utf-8"))
        for reply in replies
        for row in reply.buttons
        for button in row
    )

    # Assert
    assert longest <= TELEGRAM_CALLBACK_LIMIT
