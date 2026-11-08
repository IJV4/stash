import pytest
from builders import (
    LATER,
    an_item,
)


def test_grouped_under_itself_says_an_item_cannot_be_its_own_parent() -> None:
    # Setup
    item = an_item(id="i1")

    # Execute / Assert
    with pytest.raises(
        ValueError, match="groups are one level deep: an item cannot be its own parent"
    ):
        item.grouped_under(item, LATER)


def test_grouped_under_another_object_with_the_same_id_raises_value_error() -> None:
    # Setup
    item = an_item(id="i1")
    same_id = an_item(id="i1", title="Another title")

    # Execute / Assert
    with pytest.raises(ValueError, match="groups are one level deep"):
        item.grouped_under(same_id, LATER)


def test_ungrouped_clears_the_parent_id() -> None:
    # Setup
    item = an_item(parent_id="p1")

    # Execute
    ungrouped = item.ungrouped(LATER)

    # Assert
    assert ungrouped.parent_id is None


def test_ungrouped_changes_nothing_but_parent_id_and_updated_at() -> None:
    # Setup
    item = an_item(parent_id="p1", tags=("food",))

    # Execute
    ungrouped = item.ungrouped(LATER)

    # Assert
    assert ungrouped == an_item(tags=("food",), updated_at=LATER)


def test_ungrouped_on_an_item_without_a_parent_only_stamps_updated_at() -> None:
    # Setup
    item = an_item()

    # Execute
    ungrouped = item.ungrouped(LATER)

    # Assert
    assert ungrouped == an_item(updated_at=LATER)
