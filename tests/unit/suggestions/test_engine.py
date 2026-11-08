import logging

import pytest
from builders import BASE, LOS_ANGELES, NAIVE
from fakes.chat_model import FakeChatModel
from fakes.model_source import FakeModelSource
from log_records import recording_logs
from suggestion_builders import CONTEXT, DUNE_ID, RAMEN_ID, a_want_to, picks_reply
from suggestion_rig import an_engine

from stash.llm import LlmBadOutput, LlmDeferred, LlmUnavailable
from stash.suggestions import SuggestionEngine

ENGINE_LOGGER = "stash.suggestions.engine"
MODEL_OUTPUT = "sk-secret-model-output {not json"
CANDIDATES = [a_want_to(DUNE_ID, title="Dune"), a_want_to(RAMEN_ID, title="Ramen")]


@pytest.mark.parametrize("limit", [0, -1])
def test_a_limit_under_one_is_refused(limit: int) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="limit"):
        an_engine(FakeChatModel(picks_reply())).pick(CANDIDATES, CONTEXT, limit=limit)


def test_a_limit_under_one_is_refused_before_the_model_is_asked() -> None:
    # Setup
    model = FakeChatModel(picks_reply())

    # Execute
    with pytest.raises(ValueError, match="limit"):
        an_engine(model).pick(CANDIDATES, CONTEXT, limit=0)

    # Assert
    assert model.calls == []


def test_an_unusable_model_answer_suggests_nothing() -> None:
    # Setup
    engine = an_engine(FakeChatModel(error=LlmBadOutput(MODEL_OUTPUT)))

    # Execute
    suggestions = engine.pick(CANDIDATES, CONTEXT)

    # Assert
    assert suggestions == ()


def test_an_unusable_answer_is_logged_naming_only_the_error_class() -> None:
    # Setup
    engine = an_engine(FakeChatModel(error=LlmBadOutput(MODEL_OUTPUT)))

    # Execute
    with recording_logs(ENGINE_LOGGER) as recorder:
        engine.pick(CANDIDATES, CONTEXT)

    # Assert
    assert recorder.entries() == [
        (logging.WARNING, "suggestion model gave unusable output: LlmBadOutput")
    ]


@pytest.mark.parametrize("error", [LlmUnavailable("down"), LlmDeferred("busy")], ids=repr)
def test_a_model_that_cannot_be_reached_propagates(error: LlmUnavailable) -> None:
    # Setup
    engine = SuggestionEngine(
        FakeModelSource(FakeChatModel(), error=error), lambda: BASE, LOS_ANGELES
    )

    # Execute / Assert
    with pytest.raises(type(error)):
        engine.pick(CANDIDATES, CONTEXT)


def test_a_clock_without_a_time_zone_is_refused() -> None:
    # Setup
    engine = an_engine(FakeChatModel(picks_reply()), lambda: NAIVE)

    # Execute / Assert
    with pytest.raises(ValueError, match="clock"):
        engine.pick(CANDIDATES, CONTEXT)
