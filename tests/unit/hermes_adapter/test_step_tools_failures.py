import json
from typing import Any

import pytest
from fakes.recording_step_planner import RecordingStepPlanner
from step_builders import a_step

from stash.hermes_adapter.step_tools import StepTools
from stash.planning.errors import UnknownItem, UnknownStep

LOGGER = "stash.hermes_adapter.step_tools"
COULD_NOT_UPDATE = {"error": "the stash could not be updated"}
CALLS = [
    ("stash_add_step", {"item_id": "i1", "text": "Book", "lead_days": 7}),
    ("stash_edit_step", {"step_id": "s1", "text": "Book"}),
    ("stash_complete_step", {"step_id": "s1"}),
]


def answer_of(tool: str, arguments: Any, error: Exception) -> dict[str, Any]:
    specs = {
        spec.schema["name"]: spec
        for spec in StepTools(RecordingStepPlanner(a_step(), error)).specs()
    }
    answer: dict[str, Any] = json.loads(specs[tool].handler(arguments))
    return answer


@pytest.mark.parametrize(("tool", "arguments"), CALLS)
def test_an_unknown_item_or_step_is_answered_as_an_error(tool: str, arguments: Any) -> None:
    # Execute
    answers = [
        answer_of(tool, arguments, error) for error in (UnknownItem("i1"), UnknownStep("s1"))
    ]

    # Assert
    assert answers == [{"error": "no item 'i1'"}, {"error": "no step 's1'"}]
