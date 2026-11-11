import pytest
from builders import BASE, LOS_ANGELES, NAIVE
from fakes.chat_model import FakeChatModel
from fakes.model_source import FakeModelSource
from planning_builders import a_date_night, a_proposer, steps_reply

from stash.llm import LlmBadOutput, LlmDeferred, LlmUnavailable
from stash.planning import StepProposer


def test_the_proposer_clamps_what_the_model_answered() -> None:
    # Execute
    steps = a_proposer(FakeChatModel(steps_reply(50))).propose(a_date_night())

    # Assert
    assert len(steps) == 10


def test_an_unusable_model_answer_propagates() -> None:
    # Setup
    proposer = a_proposer(FakeChatModel(error=LlmBadOutput("not json")))

    # Execute / Assert
    with pytest.raises(LlmBadOutput):
        proposer.propose(a_date_night())


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
