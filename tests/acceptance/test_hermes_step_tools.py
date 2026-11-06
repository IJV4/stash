from collections.abc import Mapping
from typing import Any

import pytest
from app_builders import an_app, stored
from fakes.hermes_ctx import RegisteredTool
from fakes.memory_store import MemoryStore
from hermes_registration_rig import register_stash
from planning_builders import DATE_NIGHT_ID, a_date_night
from step_builders import a_step
from tool_rig import calling

from stash.domain import Step

ADDED_TEXT = "Book the table"
FIXED_TEXT = "Book the table for two"
SECOND_TEXT = "Buy tickets"


def an_app_with_a_date_night() -> tuple[MemoryStore, Mapping[str, RegisteredTool]]:
    store = stored(a_date_night())
    return store, register_stash(an_app(store=store)).ctx.tools


def stored_summary(steps: list[Step]) -> list[tuple[str, int | None, bool, bool, int]]:
    return [(step.text, step.lead_days, step.confirmed, step.done, step.position) for step in steps]


def test_the_agent_adds_edits_and_completes_steps_through_the_registered_tools() -> None:
    # Setup
    store, tools = an_app_with_a_date_night()

    # Execute
    first = calling(
        tools, "stash_add_step", {"item_id": DATE_NIGHT_ID, "text": ADDED_TEXT, "lead_days": 7}
    )["step"]
    second = calling(
        tools, "stash_add_step", {"item_id": DATE_NIGHT_ID, "text": SECOND_TEXT, "lead_days": 3}
    )["step"]
    calling(tools, "stash_edit_step", {"step_id": first["id"], "text": FIXED_TEXT})
    calling(tools, "stash_complete_step", {"step_id": second["id"]})

    # Assert
    assert stored_summary(store.steps_for(DATE_NIGHT_ID)) == [
        (FIXED_TEXT, 7, True, False, 0),
        (SECOND_TEXT, 3, True, True, 1),
    ]


BAD_CALLS = [
    ("stash_add_step", {"item_id": DATE_NIGHT_ID, "text": ADDED_TEXT}),
    ("stash_edit_step", {"step_id": "s1"}),
    ("stash_edit_step", {"step_id": "ghost", "text": FIXED_TEXT}),
]


@pytest.mark.parametrize(("tool", "arguments"), BAD_CALLS)
def test_a_bad_step_tool_call_answers_an_error_and_changes_no_step(
    tool: str, arguments: dict[str, Any]
) -> None:
    # Setup
    store, tools = an_app_with_a_date_night()
    store.save_step(a_step(item_id=DATE_NIGHT_ID, confirmed=True))
    before = store.steps_for(DATE_NIGHT_ID)

    # Execute
    answer = calling(tools, tool, arguments)

    # Assert
    assert (list(answer), store.steps_for(DATE_NIGHT_ID)) == (["error"], before)
