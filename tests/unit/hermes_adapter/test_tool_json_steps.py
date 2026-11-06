import json
import logging
from datetime import date

from step_builders import a_step

from stash.hermes_adapter.tool_arguments import ToolArguments
from stash.hermes_adapter.tool_json import UNWRITABLE, answering, step_answer, step_payload
from stash.planning.errors import PlanningRefused, UnknownItem, UnknownStep

LOGGER = logging.getLogger("tests.tool_json_steps")


def refusing_with(error: Exception) -> str:
    def work(arguments: ToolArguments) -> str:
        raise error

    return answering({}, UNWRITABLE, work, LOGGER)


def test_a_step_payload_carries_every_field_the_agent_needs() -> None:
    # Execute
    payload = step_payload(
        a_step(id="s1", item_id="i1", text="Book", lead_days=7, confirmed=True, position=2)
    )

    # Assert
    assert payload == {
        "id": "s1",
        "item_id": "i1",
        "text": "Book",
        "lead_days": 7,
        "due_on": None,
        "confirmed": True,
        "done": False,
        "position": 2,
    }


def test_a_step_payload_writes_the_due_date_as_iso_text() -> None:
    # Execute
    payload = step_payload(a_step(lead_days=None, due_on=date(2027, 2, 5)))

    # Assert
    assert payload["due_on"] == "2027-02-05"


def test_a_step_answer_wraps_the_payload_under_step() -> None:
    # Setup
    step = a_step()

    # Execute
    answer = json.loads(step_answer(step))

    # Assert
    assert answer == {"step": step_payload(step)}


def test_a_step_answer_keeps_non_ascii_text_readable() -> None:
    # Execute
    answer = step_answer(a_step(text="Réserver"))

    # Assert
    assert "Réserver" in answer


def test_a_planning_refusal_is_answered_as_an_error_with_its_message() -> None:
    # Execute
    answer = refusing_with(PlanningRefused("text must not be blank"))

    # Assert
    assert json.loads(answer) == {"error": "text must not be blank"}


def test_an_unknown_item_is_answered_as_an_error_naming_it() -> None:
    # Execute
    answer = refusing_with(UnknownItem("ghost"))

    # Assert
    assert json.loads(answer) == {"error": "no item 'ghost'"}


def test_an_unknown_step_is_answered_as_an_error_naming_it() -> None:
    # Execute
    answer = refusing_with(UnknownStep("ghost"))

    # Assert
    assert json.loads(answer) == {"error": "no step 'ghost'"}
