from datetime import date

import pytest
from builders import BASE, LATER, NAIVE, a_capture, a_filing, an_item

from stash.domain.item import Filing, Item, ItemType, Stage

PLANNED_FOR = date(2026, 11, 14)


def an_item_from_filing(filing: Filing | None = None) -> Item:
    return Item.from_filing(
        item_id="i9",
        capture=a_capture(id="c9", text="Ramen in Shibuya, so good"),
        filing=a_filing() if filing is None else filing,
        source_url="https://example.com/ramen",
        now=LATER,
    )


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


def test_item_planned_with_a_date_is_accepted() -> None:
    # Setup / Execute
    item = an_item(stage=Stage.PLANNED, date=PLANNED_FOR)

    # Assert
    assert item.date == PLANNED_FOR


def test_item_with_naive_created_at_raises_value_error() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="created_at"):
        an_item(created_at=NAIVE)


def test_item_with_naive_updated_at_raises_value_error() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="updated_at"):
        an_item(updated_at=NAIVE)


def test_item_details_do_not_change_when_the_source_dict_is_mutated() -> None:
    # Setup
    source = {"city": "Tokyo"}
    item = an_item(details=source)

    # Execute
    source["city"] = "Osaka"

    # Assert
    assert dict(item.details) == {"city": "Tokyo"}


def test_item_details_cannot_be_modified_through_the_item() -> None:
    # Setup
    item = an_item(details={"city": "Tokyo"})

    # Execute / Assert
    with pytest.raises(TypeError):
        item.details["city"] = "Osaka"  # type: ignore[index]


def test_item_tags_ignore_later_changes_to_the_list_they_were_built_from() -> None:
    # Setup
    tags = ["food"]
    item = an_item(tags=tags)

    # Execute
    tags.append("ramen")

    # Assert
    assert item == an_item(tags=("food",))


def test_item_people_ignore_later_changes_to_the_list_they_were_built_from() -> None:
    # Setup
    people = ["Ana"]
    item = an_item(people=people)

    # Execute
    people.append("Ben")

    # Assert
    assert item == an_item(people=("Ana",))


def test_items_built_from_equal_details_are_equal() -> None:
    # Setup
    first = an_item(details={"city": "Tokyo"})
    second = an_item(details={"city": "Tokyo"})

    # Assert
    assert first == second


def test_items_built_from_different_details_are_not_equal() -> None:
    # Setup
    first = an_item(details={"city": "Tokyo"})
    second = an_item(details={"city": "Osaka"})

    # Assert
    assert first != second


def test_moved_to_returns_item_in_the_new_stage() -> None:
    # Setup
    item = an_item(stage=Stage.WANT_TO)

    # Execute
    moved = item.moved_to(Stage.DONE, LATER)

    # Assert
    assert moved.stage is Stage.DONE


def test_moved_to_stamps_updated_at_with_now() -> None:
    # Setup
    item = an_item()

    # Execute
    moved = item.moved_to(Stage.DONE, LATER)

    # Assert
    assert moved.updated_at == LATER


def test_moved_to_keeps_created_at() -> None:
    # Setup
    item = an_item()

    # Execute
    moved = item.moved_to(Stage.DONE, LATER)

    # Assert
    assert moved.created_at == BASE


def test_moved_to_changes_nothing_but_stage_and_updated_at() -> None:
    # Setup
    item = an_item()

    # Execute
    moved = item.moved_to(Stage.DONE, LATER)

    # Assert
    assert moved == an_item(stage=Stage.DONE, updated_at=LATER)


def test_moved_to_leaves_the_original_item_unchanged() -> None:
    # Setup
    item = an_item(stage=Stage.WANT_TO)

    # Execute
    item.moved_to(Stage.DONE, LATER)

    # Assert
    assert item == an_item(stage=Stage.WANT_TO)


def test_moved_to_planned_without_a_date_raises_value_error() -> None:
    # Setup
    item = an_item(date=None)

    # Execute / Assert
    with pytest.raises(ValueError, match="planned items need a date"):
        item.moved_to(Stage.PLANNED, LATER)


def test_moved_to_planned_with_a_date_returns_planned_item() -> None:
    # Setup
    item = an_item(date=PLANNED_FOR)

    # Execute
    moved = item.moved_to(Stage.PLANNED, LATER)

    # Assert
    assert moved.stage is Stage.PLANNED


def test_moved_to_with_naive_now_raises_value_error() -> None:
    # Setup
    item = an_item()

    # Execute / Assert
    with pytest.raises(ValueError, match="updated_at"):
        item.moved_to(Stage.DONE, NAIVE)


def test_retyped_returns_item_of_the_new_type() -> None:
    # Setup
    item = an_item(item_type=ItemType.PLACE)

    # Execute
    retyped = item.retyped(ItemType.RECIPE, LATER)

    # Assert
    assert retyped.item_type is ItemType.RECIPE


def test_retyped_stamps_updated_at_with_now() -> None:
    # Setup
    item = an_item()

    # Execute
    retyped = item.retyped(ItemType.RECIPE, LATER)

    # Assert
    assert retyped.updated_at == LATER


def test_retyped_changes_nothing_but_type_and_updated_at() -> None:
    # Setup
    item = an_item()

    # Execute
    retyped = item.retyped(ItemType.RECIPE, LATER)

    # Assert
    assert retyped == an_item(item_type=ItemType.RECIPE, updated_at=LATER)


def test_retyped_leaves_the_original_item_unchanged() -> None:
    # Setup
    item = an_item(item_type=ItemType.PLACE)

    # Execute
    item.retyped(ItemType.RECIPE, LATER)

    # Assert
    assert item == an_item(item_type=ItemType.PLACE)


def test_from_filing_takes_type_title_and_stage_from_the_filing() -> None:
    # Setup
    filing = a_filing(title="Pho in Hanoi", stage=Stage.DOING)

    # Execute
    item = an_item_from_filing(filing)

    # Assert
    assert (item.item_type, item.title, item.stage) == (ItemType.PLACE, "Pho in Hanoi", Stage.DOING)


def test_from_filing_takes_details_tags_people_and_date_from_the_filing() -> None:
    # Setup
    filing = a_filing(
        stage=Stage.PLANNED,
        date=PLANNED_FOR,
        details={"city": "Hanoi"},
        tags=("food", "ramen"),
        people=("Ana",),
    )

    # Execute
    item = an_item_from_filing(filing)

    # Assert
    assert (dict(item.details), item.tags, item.people, item.date) == (
        {"city": "Hanoi"},
        ("food", "ramen"),
        ("Ana",),
        PLANNED_FOR,
    )


def test_from_filing_takes_the_note_from_the_capture_text() -> None:
    # Setup / Execute
    item = an_item_from_filing()

    # Assert
    assert item.note == "Ramen in Shibuya, so good"


def test_from_filing_links_the_item_to_its_capture() -> None:
    # Setup / Execute
    item = an_item_from_filing()

    # Assert
    assert item.capture_id == "c9"


def test_from_filing_carries_the_given_id_and_source_url() -> None:
    # Setup / Execute
    item = an_item_from_filing()

    # Assert
    assert (item.id, item.source_url) == ("i9", "https://example.com/ramen")


def test_from_filing_allows_a_missing_source_url() -> None:
    # Setup / Execute
    item = Item.from_filing("i9", a_capture(), a_filing(), None, LATER)

    # Assert
    assert item.source_url is None


def test_from_filing_stamps_created_at_and_updated_at_with_now() -> None:
    # Setup / Execute
    item = an_item_from_filing()

    # Assert
    assert (item.created_at, item.updated_at) == (LATER, LATER)


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
