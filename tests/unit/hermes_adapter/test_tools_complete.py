from typing import Any

from clocks import EVENING_IN_LOS_ANGELES
from fakes.store_factories import FreshStore
from tool_rig import (
    DONE_ITEM,
    WANT_TO_ITEM,
    a_tool_store,
    answer_of,
    lifecycle_tools_over,
)

FIRST_OUTCOME_ID = f"{1:032x}"


def completed(arguments: dict[str, Any], store: FreshStore | None = None) -> dict[str, Any]:
    tools = lifecycle_tools_over(store or a_tool_store())
    return answer_of(tools.complete({"item_id": WANT_TO_ITEM, **arguments}))


def test_complete_answers_the_item_the_outcome_and_whether_it_repeats() -> None:
    # Execute
    answer = completed(
        {"rating": 4, "notes": "Slow start", "takeaways": ["Start small"], "keep": True}
    )

    # Assert
    assert answer == {
        "item": {
            "id": "w1",
            "type": "book",
            "title": "Dune",
            "stage": "done",
            "date": None,
            "kept": True,
            "in_library": True,
            "parent_id": None,
            "drop_reason": None,
            "source_url": None,
            "note": "",
            "details": {},
        },
        "outcome": {
            "id": FIRST_OUTCOME_ID,
            "completed_on": "2026-11-02",
            "rating": 4,
            "notes": "Slow start",
            "takeaways": ["Start small"],
        },
        "repeat": False,
    }


def test_complete_records_exactly_one_outcome_in_the_store() -> None:
    # Setup
    store = a_tool_store()

    # Execute
    completed({"rating": 4}, store)

    # Assert
    assert [outcome.rating for outcome in store.outcomes_for(WANT_TO_ITEM)] == [4]


def test_complete_without_options_records_no_rating_notes_or_takeaways() -> None:
    # Execute
    answer = completed({})

    # Assert
    assert answer["outcome"] | {"id": None, "completed_on": None} == {
        "id": None,
        "completed_on": None,
        "rating": None,
        "notes": "",
        "takeaways": [],
    }


def test_complete_without_keep_leaves_the_item_out_of_the_library() -> None:
    # Execute
    answer = completed({"rating": 4})

    # Assert
    assert answer["item"]["in_library"] is False


def test_complete_with_a_date_records_it_as_the_day_it_was_finished() -> None:
    # Execute
    answer = completed({"completed_on": "2026-10-01"})

    # Assert
    assert answer["outcome"]["completed_on"] == "2026-10-01"


def test_completing_an_item_that_is_already_done_answers_a_repeat() -> None:
    # Setup
    tools = lifecycle_tools_over(a_tool_store())

    # Execute
    answer = answer_of(tools.complete({"item_id": DONE_ITEM, "rating": 5}))

    # Assert
    assert answer["repeat"] is True


def test_completing_an_unknown_item_answers_an_error_naming_it() -> None:
    # Execute
    answer = answer_of(lifecycle_tools_over(a_tool_store()).complete({"item_id": "zz"}))

    # Assert
    assert answer == {"error": "no item 'zz'"}


def test_completing_with_a_rating_outside_the_scale_answers_the_domains_refusal() -> None:
    # Execute
    answer = completed({"rating": 6})

    # Assert
    assert answer == {"error": "rating must be between 1 and 5"}


def test_completing_with_too_many_takeaways_answers_the_domains_refusal() -> None:
    # Execute
    answer = completed({"takeaways": [f"point {number}" for number in range(21)]})

    # Assert
    assert answer == {"error": "takeaways must have at most 20 entries"}


def test_completing_with_notes_that_are_too_long_answers_the_domains_refusal() -> None:
    # Execute
    answer = completed({"notes": "x" * 4001})

    # Assert
    assert answer == {"error": "notes must be at most 4000 characters"}


def test_completing_with_a_takeaway_that_is_too_long_answers_the_domains_refusal() -> None:
    # Execute
    answer = completed({"takeaways": ["x" * 501]})

    # Assert
    assert answer == {"error": "takeaway must be at most 500 characters"}


def completed_in_the_evening(completed_on: str, store: FreshStore) -> dict[str, Any]:
    tools = lifecycle_tools_over(store, clock=lambda: EVENING_IN_LOS_ANGELES)
    return answer_of(tools.complete({"item_id": WANT_TO_ITEM, "completed_on": completed_on}))


def test_complete_dated_the_day_after_the_local_today_is_recorded() -> None:
    # Execute
    answer = completed_in_the_evening("2026-11-03", a_tool_store())

    # Assert
    assert answer["outcome"]["completed_on"] == "2026-11-03"


def test_complete_dated_two_days_after_the_local_today_answers_an_error() -> None:
    # Execute
    answer = completed_in_the_evening("2026-11-04", a_tool_store())

    # Assert
    assert answer == {"error": "completed_on 2026-11-04 is after tomorrow"}


def test_complete_dated_in_the_future_records_no_outcome() -> None:
    # Setup
    store = a_tool_store()

    # Execute
    completed_in_the_evening("2026-11-04", store)

    # Assert
    assert store.outcomes_for(WANT_TO_ITEM) == []
