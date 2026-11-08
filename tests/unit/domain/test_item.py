from datetime import date

import pytest
from builders import BASE, LATER, NAIVE, an_item

from stash.domain.item import Stage

PLANNED_FOR = date(2026, 11, 14)


def test_item_with_empty_title_raises_value_error() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="title"):
        an_item(title="")


def test_item_with_whitespace_only_title_raises_value_error() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="title"):
        an_item(title=" \n ")


def test_item_planned_without_a_date_raises_value_error() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="planned items need a date"):
        an_item(stage=Stage.PLANNED, date=None)


def test_item_with_naive_created_at_raises_value_error() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="created_at"):
        an_item(created_at=NAIVE)


def test_item_with_naive_updated_at_raises_value_error() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="updated_at"):
        an_item(updated_at=NAIVE)


def test_moved_to_planned_without_a_date_raises_value_error() -> None:
    # Setup
    item = an_item(date=None)

    # Execute / Assert
    with pytest.raises(ValueError, match="planned items need a date"):
        item.moved_to(Stage.PLANNED, LATER)


def test_moved_to_with_naive_now_raises_value_error() -> None:
    # Setup
    item = an_item()

    # Execute / Assert
    with pytest.raises(ValueError, match="updated_at"):
        item.moved_to(Stage.DONE, NAIVE)


def test_item_tags_given_a_bare_string_raise_type_error() -> None:
    # Execute / Assert
    with pytest.raises(TypeError, match="tags must be a collection of strings"):
        an_item(tags="food")


def test_item_people_given_a_bare_string_raise_type_error() -> None:
    # Execute / Assert
    with pytest.raises(TypeError, match="people must be a collection of strings"):
        an_item(people="ab")


def test_item_with_a_datetime_for_date_raises_value_error() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="date must be a date, not a datetime"):
        an_item(date=BASE)


def test_item_with_a_source_url_that_is_not_http_raises_value_error() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="source_url"):
        an_item(source_url="javascript:alert(1)")


def test_an_undated_item_can_move_to_inbox_want_to_doing_and_dropped() -> None:
    # Setup
    item = an_item(date=None)

    # Execute / Assert
    assert item.moveable_stages() == (Stage.INBOX, Stage.WANT_TO, Stage.DOING, Stage.DROPPED)


def test_a_dated_item_can_also_move_to_planned_in_menu_order() -> None:
    # Setup
    item = an_item(date=PLANNED_FOR)

    # Execute / Assert
    assert item.moveable_stages() == (
        Stage.INBOX,
        Stage.WANT_TO,
        Stage.PLANNED,
        Stage.DOING,
        Stage.DROPPED,
    )


def test_an_undated_item_cannot_move_to_planned() -> None:
    # Execute / Assert
    assert not an_item(date=None).can_move_to(Stage.PLANNED)


def test_an_item_cannot_move_to_done_by_hand() -> None:
    # Execute / Assert
    assert not an_item(date=PLANNED_FOR).can_move_to(Stage.DONE)


def test_every_stage_an_item_can_move_to_is_a_stage_moved_to_accepts() -> None:
    # Setup
    item = an_item(date=None)

    # Execute / Assert
    assert [item.moved_to(stage, LATER).stage for stage in item.moveable_stages()] == list(
        item.moveable_stages()
    )


@pytest.mark.parametrize(
    "item_id", ["", "   ", "chat:42", "two words", "tab\there", "bell\x07", "x" * 41, "é" * 40]
)
def test_item_refuses_an_id_that_cannot_travel_in_callback_data(item_id: str) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="item id"):
        an_item(id=item_id)


@pytest.mark.parametrize(
    "capture_id", ["", "   ", "chat:42", "two words", "tab\there", "bell\x07", "x" * 41, "é" * 40]
)
def test_item_refuses_a_capture_id_that_cannot_travel_in_callback_data(capture_id: str) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="item capture id"):
        an_item(capture_id=capture_id)


def test_item_with_a_datetime_for_cool_off_until_raises_value_error() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="cool_off_until must be a date, not a datetime"):
        an_item(cool_off_until=BASE)
