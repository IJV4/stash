import pytest
from builders import LATER, an_item, fetched_item, stored_completion, stored_item, titles
from fakes.racing_item_store import RacingItemStore
from fakes.store_factories import FreshStore
from lifecycle_rig import a_lifecycle

from stash.domain import ItemType, Stage
from stash.lifecycle import LifecycleRefused


def test_finishing_a_book_with_a_rating_and_two_takeaways_moves_it_to_done_with_one_outcome() -> (
    None
):
    # Setup
    store = FreshStore()
    stored_item(store, id="book", title="Dune", item_type=ItemType.BOOK, stage=Stage.DOING)
    lifecycle = a_lifecycle(store)

    # Execute
    lifecycle.complete("book", rating=4, takeaways=("Fear is the mind-killer", "Plan for water"))

    # Assert
    history = lifecycle.history("book")
    assert (history.item.stage, [(o.rating, o.takeaways) for o in history.outcomes]) == (
        Stage.DONE,
        [(4, ("Fear is the mind-killer", "Plan for water"))],
    )


def test_making_a_kept_recipe_again_records_a_second_outcome_and_keeps_the_first_and_the_keep() -> (
    None
):
    # Setup
    store = FreshStore()
    stored_completion(store, "recipe", title="Pad thai", item_type=ItemType.RECIPE, kept=True)
    first = store.outcomes_for("recipe")[0]
    lifecycle = a_lifecycle(store, clock=lambda: LATER)

    # Execute
    again = lifecycle.complete("recipe", rating=5)

    # Assert
    history = lifecycle.history("recipe")
    assert (again.repeat, history.item.kept, history.outcomes) == (
        True,
        True,
        (first, again.outcome),
    )


def test_dropping_an_item_with_a_reason_moves_it_to_dropped_and_search_still_finds_it() -> None:
    # Setup
    store = FreshStore()
    stored_item(
        store, id="desk", title="Standing desk", item_type=ItemType.PURCHASE, stage=Stage.WANT_TO
    )
    lifecycle = a_lifecycle(store)

    # Execute
    lifecycle.drop("desk", "too expensive")

    # Assert
    found = store.search_items("standing desk")
    assert [(item.id, item.stage, item.drop_reason) for item in found] == [
        ("desk", Stage.DROPPED, "too expensive")
    ]


def test_grouping_tokyo_ramen_under_japan_trip_lists_the_ramen_among_the_trips_children() -> None:
    # Setup
    store = FreshStore()
    stored_item(store, id="trip", title="Japan trip", item_type=ItemType.PLAN)
    stored_item(store, id="ramen", title="Tokyo ramen")
    lifecycle = a_lifecycle(store)

    # Execute
    lifecycle.group("ramen", "trip")

    # Assert
    assert titles(list(lifecycle.history("trip").children)) == ["Tokyo ramen"]


def test_grouping_japan_trip_under_the_ramen_it_holds_is_refused_and_nothing_changes() -> None:
    # Setup
    store = FreshStore()
    stored_item(store, id="trip", title="Japan trip", item_type=ItemType.PLAN)
    stored_item(store, id="ramen", title="Tokyo ramen", parent_id="trip")
    before = store.list_items()
    lifecycle = a_lifecycle(store)

    # Execute
    with pytest.raises(LifecycleRefused, match="groups are one level deep"):
        lifecycle.group("trip", "ramen")

    # Assert
    assert store.list_items() == before


def test_grouping_the_ramen_under_a_trip_grouped_meanwhile_is_refused_and_nothing_is_grouped() -> (
    None
):
    # Setup
    store = RacingItemStore()
    stored_item(store, id="asia", title="Asia", item_type=ItemType.PLAN)
    stored_item(store, id="trip", title="Japan trip", item_type=ItemType.PLAN)
    stored_item(store, id="ramen", title="Tokyo ramen")
    store.another_writer_saves_before_grouping(
        an_item(id="trip", title="Japan trip", parent_id="asia", item_type=ItemType.PLAN)
    )
    lifecycle = a_lifecycle(store)

    # Execute
    with pytest.raises(LifecycleRefused, match="groups are one level deep"):
        lifecycle.group("ramen", "trip")

    # Assert
    assert fetched_item(store, "ramen").parent_id is None
