import logging

import pytest
from builders import BASE, LOS_ANGELES, NAIVE
from clocks import EVENING_IN_LOS_ANGELES
from fakes.chat_model import FakeChatModel
from fakes.model_source import FakeModelSource
from log_records import recording_logs
from planning_builders import a_date_night, a_proposer, a_raw_step, steps_reply

from stash.config import LlmTask
from stash.llm import LlmBadOutput, LlmDeferred, LlmUnavailable, TextPart
from stash.planning import STEPS_SCHEMA, ProposedStep, StepProposer
from stash.planning.schema import SCHEMA_NAME

PROPOSER_LOGGER = "stash.planning.proposer"
MODEL_OUTPUT = "sk-secret-model-output {not json"


def test_the_proposer_asks_the_suggestions_model_at_the_current_instant() -> None:
    # Setup
    source = FakeModelSource(FakeChatModel(steps_reply(1)))
    proposer = StepProposer(source, lambda: BASE, LOS_ANGELES)

    # Execute
    proposer.propose(a_date_night())

    # Assert
    assert source.requests == [(LlmTask.SUGGESTIONS, BASE)]


def test_the_proposer_returns_the_steps_the_model_answered() -> None:
    # Setup
    model = FakeChatModel({"steps": [a_raw_step(text="Book the table", lead_days=7)]})

    # Execute
    steps = a_proposer(model).propose(a_date_night())

    # Assert
    assert steps == (ProposedStep("Book the table", 7),)


def test_the_proposer_clamps_what_the_model_answered() -> None:
    # Execute
    steps = a_proposer(FakeChatModel(steps_reply(50))).propose(a_date_night())

    # Assert
    assert len(steps) == 10


def test_the_proposer_asks_for_the_steps_schema() -> None:
    # Setup
    model = FakeChatModel(steps_reply(1))

    # Execute
    a_proposer(model).propose(a_date_night())

    # Assert
    assert (model.schemas, model.schema_names) == ([STEPS_SCHEMA], [SCHEMA_NAME])


def test_the_prompt_describes_the_item_to_plan() -> None:
    # Setup
    model = FakeChatModel(steps_reply(1))

    # Execute
    a_proposer(model).propose(a_date_night(title="Anniversary dinner"))

    # Assert
    texts = [part.text for part in model.calls[0][1].parts if isinstance(part, TextPart)]
    assert "title: Anniversary dinner" in texts[0].splitlines()


def test_the_prompt_dates_today_in_the_owners_time_zone() -> None:
    # Setup
    model = FakeChatModel(steps_reply(1))
    proposer = a_proposer(model, lambda: EVENING_IN_LOS_ANGELES)

    # Execute
    proposer.propose(a_date_night())

    # Assert
    texts = [part.text for part in model.calls[0][1].parts if isinstance(part, TextPart)]
    assert texts[0].splitlines()[0] == "Today is Monday 2026-11-02."


def test_an_unusable_model_answer_proposes_nothing() -> None:
    # Setup
    proposer = a_proposer(FakeChatModel(error=LlmBadOutput(MODEL_OUTPUT)))

    # Execute
    steps = proposer.propose(a_date_night())

    # Assert
    assert steps == ()


def test_an_unusable_answer_is_logged_naming_only_the_error_class() -> None:
    # Setup
    proposer = a_proposer(FakeChatModel(error=LlmBadOutput(MODEL_OUTPUT)))

    # Execute
    with recording_logs(PROPOSER_LOGGER) as recorder:
        proposer.propose(a_date_night())

    # Assert
    assert recorder.entries() == [
        (logging.WARNING, "step model gave unusable output: LlmBadOutput")
    ]


@pytest.mark.parametrize("error", [LlmUnavailable("down"), LlmDeferred("busy")], ids=repr)
def test_a_model_that_cannot_be_reached_propagates(error: LlmUnavailable) -> None:
    # Setup
    proposer = StepProposer(
        FakeModelSource(FakeChatModel(), error=error), lambda: BASE, LOS_ANGELES
    )

    # Execute / Assert
    with pytest.raises(type(error)):
        proposer.propose(a_date_night())


def test_a_model_that_fails_while_answering_propagates() -> None:
    # Setup
    proposer = a_proposer(FakeChatModel(error=LlmUnavailable("dropped")))

    # Execute / Assert
    with pytest.raises(LlmUnavailable):
        proposer.propose(a_date_night())


def test_a_clock_without_a_time_zone_is_refused() -> None:
    # Setup
    proposer = a_proposer(FakeChatModel(steps_reply(1)), lambda: NAIVE)

    # Execute / Assert
    with pytest.raises(ValueError, match="clock"):
        proposer.propose(a_date_night())
