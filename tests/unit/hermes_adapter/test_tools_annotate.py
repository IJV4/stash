from typing import Any

from tool_rig import (
    DONE_ITEM_OUTCOME,
    a_tool_store,
    answer_of,
    lifecycle_tools_over,
)


def annotated(arguments: dict[str, Any]) -> dict[str, Any]:
    tools = lifecycle_tools_over(a_tool_store())
    return answer_of(tools.annotate({"outcome_id": DONE_ITEM_OUTCOME, **arguments}))


def test_annotating_an_unknown_outcome_answers_an_error_naming_it() -> None:
    # Execute
    answer = answer_of(
        lifecycle_tools_over(a_tool_store()).annotate({"outcome_id": "zz", "notes": ""})
    )

    # Assert
    assert answer == {"error": "no outcome 'zz'"}
