from typing import Any

from tool_rig import (
    DONE_ITEM,
    DONE_ITEM_OUTCOME,
    a_tool_store,
    answer_of,
    lifecycle_tools_over,
)


def annotated(arguments: dict[str, Any]) -> dict[str, Any]:
    tools = lifecycle_tools_over(a_tool_store())
    return answer_of(tools.annotate({"outcome_id": DONE_ITEM_OUTCOME, **arguments}))


def test_annotate_replaces_the_notes_of_the_outcome() -> None:
    # Execute
    answer = annotated({"notes": "Re-read it, better the second time"})

    # Assert
    assert answer["outcome"]["notes"] == "Re-read it, better the second time"


def test_annotate_without_takeaways_keeps_the_current_ones() -> None:
    # Execute
    answer = annotated({"notes": "New notes"})

    # Assert
    assert answer["outcome"]["takeaways"] == ["Salt early"]


def test_annotate_with_takeaways_replaces_them() -> None:
    # Execute
    answer = annotated({"notes": "New notes", "takeaways": ["One", "Two"]})

    # Assert
    assert answer["outcome"]["takeaways"] == ["One", "Two"]


def test_annotate_with_an_empty_list_of_takeaways_clears_them() -> None:
    # Execute
    answer = annotated({"notes": "New notes", "takeaways": []})

    # Assert
    assert answer["outcome"]["takeaways"] == []


def test_annotate_answers_only_the_outcome() -> None:
    # Execute
    answer = annotated({"notes": "New notes"})

    # Assert
    assert list(answer) == ["outcome"]


def test_annotate_saves_the_notes_in_the_store() -> None:
    # Setup
    store = a_tool_store()

    # Execute
    lifecycle_tools_over(store).annotate({"outcome_id": DONE_ITEM_OUTCOME, "notes": "Saved"})

    # Assert
    assert store.outcomes_for(DONE_ITEM)[0].notes == "Saved"


def test_annotating_an_unknown_outcome_answers_an_error_naming_it() -> None:
    # Execute
    answer = answer_of(
        lifecycle_tools_over(a_tool_store()).annotate({"outcome_id": "zz", "notes": ""})
    )

    # Assert
    assert answer == {"error": "no outcome 'zz'"}


def test_annotate_without_notes_keeps_the_current_notes() -> None:
    # Execute
    answer = annotated({"rating": 3})

    # Assert
    assert answer["outcome"]["notes"] == "Great"


def test_annotate_with_only_a_rating_sets_it_and_keeps_the_takeaways() -> None:
    # Execute
    answer = annotated({"rating": 3})

    # Assert
    assert (answer["outcome"]["rating"], answer["outcome"]["takeaways"]) == (3, ["Salt early"])


def test_annotate_with_only_notes_keeps_the_rating() -> None:
    # Execute
    answer = annotated({"notes": "New notes"})

    # Assert
    assert answer["outcome"]["rating"] == 4


def test_annotate_with_a_rating_saves_it_in_the_store_as_the_only_outcome() -> None:
    # Setup
    store = a_tool_store()

    # Execute
    lifecycle_tools_over(store).annotate({"outcome_id": DONE_ITEM_OUTCOME, "rating": 1})

    # Assert
    assert [outcome.rating for outcome in store.outcomes_for(DONE_ITEM)] == [1]
