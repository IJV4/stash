import pytest
from builders import (
    LATER,
    a_parent_item,
    an_item,
)

from stash.domain import GROUPS_ONE_LEVEL_DEEP


def test_grouped_under_sets_the_parent_id_to_the_parents_id() -> None:
    # Setup
    item = an_item()

    # Execute
    grouped = item.grouped_under(a_parent_item(), LATER)

    # Assert
    assert grouped.parent_id == "p1"


def test_grouped_under_changes_nothing_but_parent_id_and_updated_at() -> None:
    # Setup
    item = an_item(tags=("food",))

    # Execute
    grouped = item.grouped_under(a_parent_item(), LATER)

    # Assert
    assert grouped == an_item(tags=("food",), parent_id="p1", updated_at=LATER)


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


def test_grouped_under_a_parent_that_has_a_parent_raises_value_error() -> None:
    # Setup
    item = an_item(id="i1")
    child_of_another = an_item(id="p1", parent_id="g1")

    # Execute / Assert
    with pytest.raises(ValueError, match="groups are one level deep"):
        item.grouped_under(child_of_another, LATER)


def test_grouped_under_a_parent_that_is_a_child_of_this_item_raises_value_error() -> None:
    # Setup
    item = an_item(id="i1")
    own_child = an_item(id="p1", parent_id="i1")

    # Execute / Assert
    with pytest.raises(ValueError, match="groups are one level deep"):
        item.grouped_under(own_child, LATER)


def test_grouped_under_a_different_parent_regroups_an_already_grouped_item() -> None:
    # Setup
    item = an_item(parent_id="p1")

    # Execute
    regrouped = item.grouped_under(an_item(id="p2"), LATER)

    # Assert
    assert regrouped.parent_id == "p2"


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


def test_a_grouping_refusal_starts_with_the_exported_one_level_deep_message() -> None:
    # Setup
    item = an_item(id="i1")
    child_of_another = an_item(id="p1", parent_id="g1")

    # Execute / Assert
    with pytest.raises(ValueError, match=GROUPS_ONE_LEVEL_DEEP):
        item.grouped_under(child_of_another, LATER)
