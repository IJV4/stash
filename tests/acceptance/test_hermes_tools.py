import json

from app_builders import an_app, stored
from builders import BASE, an_item, minutes_after
from fakes.failing_list_store import FailingListStore
from hermes_rig import register_stash

from stash.domain import ItemType, Stage


def test_stash_search_returns_the_items_matching_the_query_regardless_of_case() -> None:
    # Setup
    ramen = an_item(
        id="i1",
        capture_id="c1",
        item_type=ItemType.PLACE,
        title="Ichiran ramen",
        stage=Stage.WANT_TO,
    )
    soup = an_item(id="i2", capture_id="c2", item_type=ItemType.RECIPE, title="Miso soup")
    plugin = register_stash(an_app(store=stored(ramen, soup)))

    # Execute
    answer = plugin.ctx.tools["stash_search"].handler({"query": "RAMEN"})

    # Assert
    assert json.loads(answer) == {
        "items": [
            {
                "id": "i1",
                "type": "place",
                "title": "Ichiran ramen",
                "stage": "want_to",
                "date": None,
            }
        ]
    }


def test_stash_list_returns_the_newest_matching_items_first_within_the_limit() -> None:
    # Setup
    oldest = an_item(id="i1", capture_id="c1", stage=Stage.WANT_TO, created_at=BASE)
    newer = an_item(id="i2", capture_id="c2", stage=Stage.WANT_TO, created_at=minutes_after(5))
    other_stage = an_item(id="i3", capture_id="c3", stage=Stage.INBOX, created_at=minutes_after(9))
    plugin = register_stash(an_app(store=stored(oldest, newer, other_stage)))

    # Execute
    answer = plugin.ctx.tools["stash_list"].handler({"stage": "want_to", "limit": 1})

    # Assert
    assert [item["id"] for item in json.loads(answer)["items"]] == ["i2"]


def test_a_failing_store_makes_stash_list_answer_an_error() -> None:
    # Setup
    plugin = register_stash(an_app(store=FailingListStore()))

    # Execute
    answer = plugin.ctx.tools["stash_list"].handler({})

    # Assert
    assert list(json.loads(answer)) == ["error"]
