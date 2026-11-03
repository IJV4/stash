import io

from app_builders import stored
from builders import BASE, an_item
from fakes.memory_store import MemoryStore
from stash.cli.commands import list_items

from stash.domain import ItemType, Stage
from stash.store import ItemStore


def four_items() -> MemoryStore:
    return stored(
        an_item(id="a", capture_id="ca", title="Ichiran", stage=Stage.WANT_TO, created_at=BASE),
        an_item(
            id="b",
            capture_id="cb",
            title="Lemon chicken",
            item_type=ItemType.RECIPE,
            stage=Stage.WANT_TO,
            created_at=BASE.replace(minute=1),
        ),
        an_item(
            id="c",
            capture_id="cc",
            title="Tonkatsu",
            stage=Stage.INBOX,
            created_at=BASE.replace(minute=2),
        ),
        an_item(
            id="d",
            capture_id="cd",
            title="Gyoza",
            stage=Stage.WANT_TO,
            created_at=BASE.replace(minute=3),
        ),
    )


def listed(
    store: ItemStore,
    stage: Stage | None = None,
    item_type: ItemType | None = None,
    limit: int = 20,
) -> str:
    out = io.StringIO()
    list_items(store, stage, item_type, limit, out)
    return out.getvalue()


def test_list_prints_one_line_per_item_newest_first() -> None:
    # Execute
    output = listed(four_items())

    # Assert
    assert output == (
        "Places · Gyoza · Want to\n"
        "Places · Tonkatsu · Inbox\n"
        "Recipes · Lemon chicken · Want to\n"
        "Places · Ichiran · Want to\n"
    )


def test_list_narrows_to_a_stage() -> None:
    # Execute
    output = listed(four_items(), stage=Stage.INBOX)

    # Assert
    assert output == "Places · Tonkatsu · Inbox\n"


def test_list_narrows_to_a_type() -> None:
    # Execute
    output = listed(four_items(), item_type=ItemType.RECIPE)

    # Assert
    assert output == "Recipes · Lemon chicken · Want to\n"


def test_list_caps_the_number_of_items_at_the_limit() -> None:
    # Execute
    output = listed(four_items(), limit=2)

    # Assert
    assert output == "Places · Gyoza · Want to\nPlaces · Tonkatsu · Inbox\n"


def test_list_with_nothing_to_show_prints_no_items() -> None:
    # Execute
    output = listed(MemoryStore())

    # Assert
    assert output == "No items.\n"


def test_list_exits_0() -> None:
    # Execute
    exit_code = list_items(MemoryStore(), None, None, 20, io.StringIO())

    # Assert
    assert exit_code == 0
