import json
from datetime import date
from typing import Any

import pytest
from fakes.recording_step_planner import RecordingStepPlanner
from step_builders import a_step

from stash.hermes_adapter.step_tools import StepTools
from stash.hermes_adapter.tool_spec import ToolSpec

STEP = a_step(id="s1", item_id="i1", text="Book the table", confirmed=True)


def tools_over(planner: RecordingStepPlanner) -> dict[str, ToolSpec]:
    return {spec.schema["name"]: spec for spec in StepTools(planner).specs()}


def call(planner: RecordingStepPlanner, tool: str, arguments: Any) -> dict[str, Any]:
    answer: dict[str, Any] = json.loads(tools_over(planner)[tool].handler(arguments))
    return answer


def test_adding_a_step_with_a_date_passes_the_date_not_a_lead_time() -> None:
    # Setup
    planner = RecordingStepPlanner(STEP)

    # Execute
    call(planner, "stash_add_step", {"item_id": "i1", "text": "Book", "due_on": "2027-02-05"})

    # Assert
    assert planner.calls == [
        (
            "add_step",
            {"item_id": "i1", "text": "Book", "lead_days": None, "due_on": date(2027, 2, 5)},
        )
    ]


def test_adding_a_step_with_both_a_lead_time_and_a_date_leaves_the_refusal_to_the_planner() -> None:
    # Setup
    planner = RecordingStepPlanner(STEP)

    # Execute
    call(
        planner,
        "stash_add_step",
        {"item_id": "i1", "text": "B", "lead_days": 1, "due_on": "2027-02-05"},
    )

    # Assert
    assert planner.calls == [
        (
            "add_step",
            {"item_id": "i1", "text": "B", "lead_days": 1, "due_on": date(2027, 2, 5)},
        )
    ]


def test_editing_a_step_passes_a_new_lead_time_and_a_new_date_by_their_own_names() -> None:
    # Setup
    planner = RecordingStepPlanner(STEP)

    # Execute
    call(planner, "stash_edit_step", {"step_id": "s1", "lead_days": 0, "due_on": "2027-02-05"})

    # Assert
    assert planner.calls == [
        (
            "edit_step",
            {"step_id": "s1", "text": None, "lead_days": 0, "due_on": date(2027, 2, 5)},
        )
    ]


BAD_ARGUMENTS = [
    ("stash_add_step", {"item_id": "i1", "text": "Book", "lead_days": True}),
    ("stash_add_step", {"item_id": "i1", "text": "Book", "lead_days": "7"}),
    ("stash_add_step", {"item_id": "i1", "text": "Book", "due_on": "5 Feb 2027"}),
    ("stash_add_step", {"item_id": "i1", "text": 5, "lead_days": 7}),
    ("stash_add_step", {"item_id": "i1", "lead_days": 7}),
    ("stash_add_step", {"item_id": "a:b", "text": "Book", "lead_days": 7}),
    ("stash_add_step", {"text": "Book", "lead_days": 7}),
    ("stash_add_step", "not an object"),
    ("stash_edit_step", {"step_id": "s1", "text": ["a"]}),
    ("stash_edit_step", {"step_id": "s1", "lead_days": 1.5}),
    ("stash_edit_step", {"step_id": "s1", "due_on": "tomorrow"}),
    ("stash_edit_step", {"step_id": ""}),
    ("stash_edit_step", None),
    ("stash_complete_step", {"step_id": "x" * 41}),
    ("stash_complete_step", {"step_id": "a:b"}),
    ("stash_complete_step", {}),
]


@pytest.mark.parametrize(("tool", "arguments"), BAD_ARGUMENTS)
def test_malformed_arguments_are_answered_as_an_error_without_asking_the_planner(
    tool: str, arguments: Any
) -> None:
    # Setup
    planner = RecordingStepPlanner(STEP)

    # Execute
    answer = call(planner, tool, arguments)

    # Assert
    assert (list(answer), planner.calls) == (["error"], [])
