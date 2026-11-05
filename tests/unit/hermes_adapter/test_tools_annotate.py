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
