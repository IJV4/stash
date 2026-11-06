import json
import logging
from typing import Any

import pytest
from fakes.recording_step_planner import RecordingStepPlanner
from log_records import recording_logs
from step_builders import a_step

from stash.hermes_adapter.step_tools import StepTools
from stash.planning.errors import PlanningRefused, UnknownItem, UnknownStep

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
def test_a_planning_refusal_is_answered_as_an_error_with_its_message(
    tool: str, arguments: Any
) -> None:
    # Execute
    answer = answer_of(
        tool, arguments, PlanningRefused("a step needs exactly one of lead_days and due_on")
    )

    # Assert
    assert answer == {"error": "a step needs exactly one of lead_days and due_on"}


@pytest.mark.parametrize(("tool", "arguments"), CALLS)
def test_an_unknown_item_or_step_is_answered_as_an_error(tool: str, arguments: Any) -> None:
    # Execute
    answers = [
        answer_of(tool, arguments, error) for error in (UnknownItem("i1"), UnknownStep("s1"))
    ]

    # Assert
    assert answers == [{"error": "no item 'i1'"}, {"error": "no step 's1'"}]


@pytest.mark.parametrize(("tool", "arguments"), CALLS)
def test_a_planner_that_fails_unexpectedly_is_answered_as_could_not_be_updated(
    tool: str, arguments: Any
) -> None:
    # Execute
    answer = answer_of(tool, arguments, RuntimeError("database is closed"))

    # Assert
    assert answer == COULD_NOT_UPDATE


def test_an_unexpected_planner_failure_is_logged_as_one_error() -> None:
    # Setup
    with recording_logs(LOGGER) as logs:
        # Execute
        answer_of("stash_complete_step", {"step_id": "s1"}, RuntimeError("database is closed"))

        # Assert
        assert [level for level, _ in logs.entries()] == [logging.ERROR]
