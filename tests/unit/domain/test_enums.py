import pytest

from stash.domain.item import ItemType, Stage


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
