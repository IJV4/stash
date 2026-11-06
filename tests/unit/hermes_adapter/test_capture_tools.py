from typing import Any

import pytest
from builders import a_capture, an_item
from capture_builders import SAMPLE_TEXT
from fakes.recording_agent_capturer import RecordingAgentCapturer
from log_records import recording_logs
from tool_rig import answer_of

from stash.capture import Deferred, Filed
from stash.capture.agent import AgentCaptureError
from stash.capture.replies import TELEGRAM_TEXT_LIMIT
from stash.hermes_adapter.capture_tools import CAPTURE_SCHEMA, CaptureTools
from stash.hermes_adapter.tool_json import UNWRITABLE, capture_answer
from stash.hermes_adapter.tool_schema import owners_data

DESCRIPTION_START = (
    "Save something new the owner mentions that is not in stash yet (search first); "
    "then use the returned item_id."
)
CAPTURE_LOGGER = "stash.hermes_adapter.capture_tools"
FAILURE_LOG = "a stash tool failed"
NOTE = "loved the ending"
CAPTURER_REFUSAL = "the capturer refused this"
REFUSED_ARGUMENTS = [
    {},
    {"text": 5},
    {"text": None},
    {"text": SAMPLE_TEXT, "note": 5},
    {"text": SAMPLE_TEXT, "note": ["a"]},
]
NOT_OBJECTS = [None, SAMPLE_TEXT, [SAMPLE_TEXT], 3]


def capturing(capturer: RecordingAgentCapturer, arguments: object) -> dict[str, Any]:
    return answer_of(CaptureTools(capturer).capture(arguments))


def test_the_capture_tool_is_named_stash_capture() -> None:
    # Assert
    assert CAPTURE_SCHEMA["name"] == "stash_capture"


def test_the_description_tells_the_agent_to_search_first_and_that_titles_are_the_owners_data() -> (
    None
):
    # Assert
    assert CAPTURE_SCHEMA["description"] == f"{DESCRIPTION_START} {owners_data('Titles')}"


def test_the_parameters_are_a_required_capped_text_and_an_optional_note() -> None:
    # Setup
    parameters = CAPTURE_SCHEMA["parameters"]
    properties = parameters["properties"]

    # Assert
    assert (
        parameters["required"],
        {name: spec["type"] for name, spec in properties.items()},
        properties["text"]["maxLength"],
    ) == (["text"], {"text": "string", "note": "string"}, TELEGRAM_TEXT_LIMIT)


def test_the_tool_offers_the_capture_schema_and_handler() -> None:
    # Setup
    tools = CaptureTools(RecordingAgentCapturer())

    # Execute
    [spec] = tools.specs()

    # Assert
    assert (spec.schema, spec.handler) == (CAPTURE_SCHEMA, tools.capture)


def test_a_filed_capture_answers_its_item_id_title_type_and_stage() -> None:
    # Setup
    item = an_item(id="i9", title="Tidewater Notes")

    # Execute
    answer = answer_of(capture_answer(Filed(item, unsure=False)))

    # Assert
    assert answer == {
        "item_id": "i9",
        "title": "Tidewater Notes",
        "item_type": item.item_type.value,
        "stage": item.stage.value,
    }


def test_a_deferred_capture_answers_saved_and_pending() -> None:
    # Execute
    answer = answer_of(capture_answer(Deferred(a_capture(), "ai_unavailable")))

    # Assert
    assert answer == {"saved": True, "pending": True}


def test_capturing_answers_what_the_capturer_filed() -> None:
    # Setup
    capturer = RecordingAgentCapturer()
    capturer.result = Filed(an_item(id="i9"), unsure=False)

    # Execute
    answer = capturing(capturer, {"text": SAMPLE_TEXT})

    # Assert
    assert answer["item_id"] == "i9"


def test_capturing_answers_saved_and_pending_when_the_capturer_defers() -> None:
    # Setup
    capturer = RecordingAgentCapturer()
    capturer.defers()

    # Execute
    answer = capturing(capturer, {"text": SAMPLE_TEXT})

    # Assert
    assert answer == {"saved": True, "pending": True}


def test_capturing_passes_the_text_and_note_to_the_capturer() -> None:
    # Setup
    capturer = RecordingAgentCapturer()

    # Execute
    capturing(capturer, {"text": SAMPLE_TEXT, "note": NOTE})

    # Assert
    assert capturer.calls == [(SAMPLE_TEXT, NOTE)]


def test_a_null_note_reaches_the_capturer_as_no_note() -> None:
    # Setup
    capturer = RecordingAgentCapturer()

    # Execute
    capturing(capturer, {"text": SAMPLE_TEXT, "note": None})

    # Assert
    assert capturer.calls == [(SAMPLE_TEXT, None)]


def test_capturing_accepts_the_keyword_arguments_hermes_passes() -> None:
    # Setup
    tools = CaptureTools(RecordingAgentCapturer())

    # Execute
    answer = answer_of(tools.capture({"text": SAMPLE_TEXT}, task_id="t1"))

    # Assert
    assert "item_id" in answer


@pytest.mark.parametrize("arguments", [*REFUSED_ARGUMENTS, *NOT_OBJECTS])
def test_refused_arguments_answer_an_error(arguments: object) -> None:
    # Execute
    answer = capturing(RecordingAgentCapturer(), arguments)

    # Assert
    assert list(answer) == ["error"]


@pytest.mark.parametrize("arguments", [*REFUSED_ARGUMENTS, *NOT_OBJECTS])
def test_refused_arguments_never_reach_the_capturer(arguments: object) -> None:
    # Setup
    capturer = RecordingAgentCapturer()

    # Execute
    capturing(capturer, arguments)

    # Assert
    assert capturer.calls == []


def test_a_non_text_note_is_refused_with_the_reason() -> None:
    # Execute
    answer = capturing(RecordingAgentCapturer(), {"text": SAMPLE_TEXT, "note": 5})

    # Assert
    assert answer == {"error": "note must be text"}


def test_a_missing_text_is_refused_with_the_reason() -> None:
    # Execute
    answer = capturing(RecordingAgentCapturer(), {})

    # Assert
    assert answer == {"error": "text must be text"}


def test_a_refusal_from_the_capturer_is_answered_as_an_error_with_its_message() -> None:
    # Setup
    capturer = RecordingAgentCapturer()
    capturer.error = ValueError(CAPTURER_REFUSAL)

    # Execute
    answer = capturing(capturer, {"text": SAMPLE_TEXT})

    # Assert
    assert answer == {"error": CAPTURER_REFUSAL}


def test_a_capture_that_cannot_end_as_filed_or_deferred_answers_the_unwritable_error() -> None:
    # Setup
    capturer = RecordingAgentCapturer()
    capturer.error = AgentCaptureError("cannot happen")

    # Execute
    answer = capturing(capturer, {"text": SAMPLE_TEXT})

    # Assert
    assert answer == {"error": UNWRITABLE}


def test_a_capture_that_cannot_end_as_filed_or_deferred_is_logged() -> None:
    # Setup
    capturer = RecordingAgentCapturer()
    capturer.error = AgentCaptureError("cannot happen")

    # Execute
    with recording_logs(CAPTURE_LOGGER) as recorder:
        capturing(capturer, {"text": SAMPLE_TEXT})

    # Assert
    assert [message for _, message in recorder.entries()] == [FAILURE_LOG]
