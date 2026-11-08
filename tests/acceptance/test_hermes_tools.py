import json

from app_builders import an_app, stored
from builders import BASE, an_item, an_outcome, minutes_after
from fakes.faulty_store import unlistable_store
from hermes_registration_rig import register_stash
from tool_rig import answer_of, calling, store_snapshot

from stash.domain import ItemType, Stage

LINK_DETAILS = {
    "link_title": "Black holes explained",
    "uploader": "Kurzgesagt",
    "duration": "11:02",
}


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
    plugin = register_stash(an_app(store=unlistable_store()))

    # Execute
    answer = plugin.ctx.tools["stash_list"].handler({})

    # Assert
    assert list(json.loads(answer)) == ["error"]


def test_finishing_a_book_through_the_tools_records_keeps_and_lists_it_in_the_library() -> None:
    # Setup
    dune = an_item(
        id="b1", capture_id="c1", item_type=ItemType.BOOK, title="Dune", stage=Stage.DOING
    )
    miso = an_item(
        id="r1",
        capture_id="c2",
        item_type=ItemType.RECIPE,
        title="Miso soup",
        stage=Stage.DONE,
        kept=True,
    )
    store = stored(dune, miso)
    store.add_outcome(an_outcome(id="o-r1", item_id="r1", rating=5))
    tools = register_stash(an_app(store=store)).ctx.tools

    # Execute
    [found] = calling(tools, "stash_search", {"query": "dune"})["items"]
    calling(
        tools,
        "stash_complete",
        {
            "item_id": found["id"],
            "rating": 4,
            "takeaways": ["Start small", "Fear is the mind-killer"],
            "keep": True,
        },
    )
    library = calling(tools, "stash_library", {"item_type": "book"})
    shown = calling(tools, "stash_get", {"item_id": found["id"]})

    # Assert
    assert (
        [(entry["id"], entry["rating"]) for entry in library["items"]],
        [(outcome["rating"], outcome["takeaways"]) for outcome in shown["outcomes"]],
        shown["item"]["kept"],
    ) == ([("b1", 4)], [(4, ["Start small", "Fear is the mind-killer"])], True)


def test_stash_get_shows_the_link_details_the_outcomes_with_takeaways_and_the_children() -> None:
    # Setup
    video = an_item(
        id="m1",
        capture_id="c1",
        item_type=ItemType.MEDIA,
        title="Black holes",
        stage=Stage.DONE,
        source_url="https://example.com/watch?v=1",
        details=LINK_DETAILS,
        kept=True,
    )
    part_two = an_item(id="m2", capture_id="c2", title="Part two", parent_id="m1")
    store = stored(video, part_two)
    store.add_outcome(an_outcome(id="o1", item_id="m1", takeaways=("Event horizons", "Spaghetti")))
    tools = register_stash(an_app(store=store)).ctx.tools

    # Execute
    shown = answer_of(tools["stash_get"].handler({"item_id": "m1"}))

    # Assert
    assert (
        shown["item"]["details"],
        [outcome["takeaways"] for outcome in shown["outcomes"]],
        [child["id"] for child in shown["children"]],
    ) == (
        LINK_DETAILS,
        [["Event horizons", "Spaghetti"]],
        ["m2"],
    )


def test_a_tool_call_with_bad_arguments_answers_an_error_and_changes_nothing() -> None:
    # Setup
    store = stored(an_item(id="b1", capture_id="c1", item_type=ItemType.BOOK, stage=Stage.DOING))
    tools = register_stash(an_app(store=store)).ctx.tools
    before = store_snapshot(store)

    # Execute
    answer = answer_of(tools["stash_complete"].handler({"item_id": "b1", "rating": True}))

    # Assert
    assert (list(answer), store_snapshot(store)) == (["error"], before)


def test_annotating_the_latest_outcome_adds_a_rating_and_takeaways_to_the_one_completion() -> None:
    # Setup
    dune = an_item(
        id="b1", capture_id="c1", item_type=ItemType.BOOK, title="Dune", stage=Stage.DONE
    )
    store = stored(dune)
    store.add_outcome(
        an_outcome(
            id="o-b1", item_id="b1", rating=None, notes="Finished on the train", takeaways=()
        )
    )
    tools = register_stash(an_app(store=store)).ctx.tools

    # Execute
    latest = calling(tools, "stash_get", {"item_id": "b1"})["outcomes"][-1]
    calling(
        tools,
        "stash_annotate",
        {"outcome_id": latest["id"], "rating": 4, "takeaways": ["Start small", "Fear"]},
    )
    shown = calling(tools, "stash_get", {"item_id": "b1"})

    # Assert
    assert [
        (outcome["rating"], outcome["takeaways"], outcome["notes"]) for outcome in shown["outcomes"]
    ] == [(4, ["Start small", "Fear"], "Finished on the train")]
