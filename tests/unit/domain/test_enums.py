import pytest

from stash.domain.item import ItemType, Stage


@pytest.mark.parametrize(
    ("item_type", "label"),
    [
        (ItemType.PLACE, "Places"),
        (ItemType.RECIPE, "Recipes"),
        (ItemType.PURCHASE, "Purchases"),
        (ItemType.LEARN, "Learning"),
        (ItemType.BOOK, "Books"),
        (ItemType.MEDIA, "Media"),
        (ItemType.IDEA, "Ideas"),
        (ItemType.PLAN, "Plans"),
        (ItemType.ACTIVITY, "Activities"),
        (ItemType.GIFT, "Gifts"),
        (ItemType.OTHER, "Other"),
    ],
)
def test_item_type_label_is_its_plural_display_name(item_type: ItemType, label: str) -> None:
    # Assert
    assert item_type.label == label


@pytest.mark.parametrize(
    ("stage", "label"),
    [
        (Stage.INBOX, "Inbox"),
        (Stage.WANT_TO, "Want to"),
        (Stage.PLANNED, "Planned"),
        (Stage.DOING, "Doing"),
        (Stage.DONE, "Done"),
        (Stage.DROPPED, "Dropped"),
    ],
)
def test_stage_label_is_its_display_name(stage: Stage, label: str) -> None:
    # Assert
    assert stage.label == label


@pytest.mark.parametrize(
    ("member", "value"),
    [
        (ItemType.PLACE, "place"),
        (ItemType.RECIPE, "recipe"),
        (ItemType.PURCHASE, "purchase"),
        (ItemType.LEARN, "learn"),
        (ItemType.BOOK, "book"),
        (ItemType.MEDIA, "media"),
        (ItemType.IDEA, "idea"),
        (ItemType.PLAN, "plan"),
        (ItemType.ACTIVITY, "activity"),
        (ItemType.GIFT, "gift"),
        (ItemType.OTHER, "other"),
        (Stage.INBOX, "inbox"),
        (Stage.WANT_TO, "want_to"),
        (Stage.PLANNED, "planned"),
        (Stage.DOING, "doing"),
        (Stage.DONE, "done"),
        (Stage.DROPPED, "dropped"),
    ],
)
def test_enum_member_serialises_to_its_stored_value(member: str, value: str) -> None:
    # Assert
    assert member == value
