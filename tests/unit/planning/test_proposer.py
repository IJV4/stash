import logging

import pytest
from builders import BASE, LOS_ANGELES, NAIVE
from fakes.chat_model import FakeChatModel
from fakes.model_source import FakeModelSource
from log_records import recording_logs
from planning_builders import a_date_night, a_proposer, steps_reply

from stash.llm import LlmBadOutput, LlmDeferred, LlmUnavailable
from stash.planning import StepProposer

PROPOSER_LOGGER = "stash.planning.proposer"
MODEL_OUTPUT = "sk-secret-model-output {not json"


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


def test_a_clock_without_a_time_zone_is_refused() -> None:
    # Setup
    proposer = a_proposer(FakeChatModel(steps_reply(1)), lambda: NAIVE)

    # Execute / Assert
    with pytest.raises(ValueError, match="clock"):
        proposer.propose(a_date_night())
