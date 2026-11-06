import logging

import pytest
from builders import BASE, LOS_ANGELES, NAIVE
from clocks import EVENING_IN_LOS_ANGELES
from fakes.chat_model import FakeChatModel
from fakes.model_source import FakeModelSource
from log_records import recording_logs
from suggestion_builders import CONTEXT, DUNE_ID, RAMEN_ID, a_raw_pick, a_want_to, picks_reply
from suggestion_rig import an_engine

from stash.config import LlmTask
from stash.llm import LlmBadOutput, LlmDeferred, LlmUnavailable, TextPart
from stash.suggestions import Suggestion, SuggestionEngine
from stash.suggestions.schema import SCHEMA_NAME, SUGGESTIONS_SCHEMA

ENGINE_LOGGER = "stash.suggestions.engine"
MODEL_OUTPUT = "sk-secret-model-output {not json"
CANDIDATES = [a_want_to(DUNE_ID, title="Dune"), a_want_to(RAMEN_ID, title="Ramen")]


def prompt_lines(model: FakeChatModel, index: int) -> list[str]:
    part = model.calls[0][index].parts[0]
    assert isinstance(part, TextPart)
    return part.text.splitlines()


def test_the_engine_asks_the_suggestions_model_at_the_current_instant() -> None:
    # Setup
    source = FakeModelSource(FakeChatModel(picks_reply()))
    engine = SuggestionEngine(source, lambda: BASE, LOS_ANGELES)

    # Execute
    engine.pick(CANDIDATES, CONTEXT)

    # Assert
    assert source.requests == [(LlmTask.SUGGESTIONS, BASE)]


def test_the_engine_returns_the_suggestions_the_model_answered() -> None:
    # Setup
    model = FakeChatModel(picks_reply(a_raw_pick(RAMEN_ID, "Hot and close")))

    # Execute
    suggestions = an_engine(model).pick(CANDIDATES, CONTEXT)

    # Assert
    assert suggestions == (Suggestion(RAMEN_ID, "Hot and close"),)


def test_the_engine_drops_an_id_that_is_not_among_the_candidates() -> None:
    # Setup
    model = FakeChatModel(picks_reply(a_raw_pick("invented"), a_raw_pick(DUNE_ID)))

    # Execute
    suggestions = an_engine(model).pick([a_want_to(DUNE_ID)], CONTEXT)

    # Assert
    assert [suggestion.item_id for suggestion in suggestions] == [DUNE_ID]


def test_the_engine_keeps_at_most_the_limit() -> None:
    # Setup
    model = FakeChatModel(picks_reply(a_raw_pick(DUNE_ID), a_raw_pick(RAMEN_ID)))

    # Execute
    suggestions = an_engine(model).pick(CANDIDATES, CONTEXT, limit=1)

    # Assert
    assert [suggestion.item_id for suggestion in suggestions] == [DUNE_ID]


def test_the_limit_defaults_to_three() -> None:
    # Setup
    candidates = [a_want_to(f"item{n}") for n in range(5)]
    model = FakeChatModel(picks_reply(*(a_raw_pick(c.id) for c in candidates)))

    # Execute
    suggestions = an_engine(model).pick(candidates, CONTEXT)

    # Assert
    assert len(suggestions) == 3


def test_the_engine_tells_the_model_the_limit() -> None:
    # Setup
    model = FakeChatModel(picks_reply())

    # Execute
    an_engine(model).pick(CANDIDATES, CONTEXT, limit=2)

    # Assert
    assert any("at most 2 picks" in line for line in prompt_lines(model, 0))


def test_the_engine_asks_for_the_suggestions_schema() -> None:
    # Setup
    model = FakeChatModel(picks_reply())

    # Execute
    an_engine(model).pick(CANDIDATES, CONTEXT)

    # Assert
    assert (model.schemas, model.schema_names) == ([SUGGESTIONS_SCHEMA], [SCHEMA_NAME])


def test_the_prompt_offers_every_candidate() -> None:
    # Setup
    model = FakeChatModel(picks_reply())

    # Execute
    an_engine(model).pick(CANDIDATES, CONTEXT)

    # Assert
    assert prompt_lines(model, 1)[2:] == [
        '<item id="dune" type="place">Dune</item>',
        '<item id="ramen" type="place">Ramen</item>',
    ]


def test_the_prompt_carries_the_context() -> None:
    # Setup
    model = FakeChatModel(picks_reply())

    # Execute
    an_engine(model).pick(CANDIDATES, CONTEXT)

    # Assert
    assert prompt_lines(model, 1)[1] == f"<context>{CONTEXT}</context>"


def test_the_prompt_dates_today_in_the_owners_time_zone() -> None:
    # Setup
    model = FakeChatModel(picks_reply())
    engine = an_engine(model, lambda: EVENING_IN_LOS_ANGELES)

    # Execute
    engine.pick(CANDIDATES, CONTEXT)

    # Assert
    assert prompt_lines(model, 1)[0] == "Today is Monday 2026-11-02."


def test_with_no_candidates_the_engine_suggests_nothing() -> None:
    # Execute
    suggestions = an_engine(FakeChatModel(picks_reply(a_raw_pick(DUNE_ID)))).pick([], CONTEXT)

    # Assert
    assert suggestions == ()


def test_with_no_candidates_the_model_is_not_asked() -> None:
    # Setup
    model = FakeChatModel(picks_reply())
    source = FakeModelSource(model)

    # Execute
    SuggestionEngine(source, lambda: BASE, LOS_ANGELES).pick([], CONTEXT)

    # Assert
    assert (source.requests, model.calls) == ([], [])


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


@pytest.mark.parametrize("error", [LlmUnavailable("dropped"), LlmDeferred("busy")], ids=repr)
def test_a_model_that_fails_while_answering_propagates(error: LlmUnavailable) -> None:
    # Setup
    engine = an_engine(FakeChatModel(error=error))

    # Execute / Assert
    with pytest.raises(type(error)):
        engine.pick(CANDIDATES, CONTEXT)


def test_a_clock_without_a_time_zone_is_refused() -> None:
    # Setup
    engine = an_engine(FakeChatModel(picks_reply()), lambda: NAIVE)

    # Execute / Assert
    with pytest.raises(ValueError, match="clock"):
        engine.pick(CANDIDATES, CONTEXT)


def test_an_answer_with_no_usable_pick_is_logged_without_the_model_text() -> None:
    # Setup
    engine = an_engine(FakeChatModel(picks_reply(a_raw_pick("invented", "sk-secret-reason"))))

    # Execute
    with recording_logs(ENGINE_LOGGER) as recorder:
        engine.pick(CANDIDATES, CONTEXT)

    # Assert
    assert recorder.entries() == [(logging.WARNING, "suggestion model gave no usable pick")]


def test_an_answer_with_a_usable_pick_logs_nothing() -> None:
    # Setup
    engine = an_engine(FakeChatModel(picks_reply(a_raw_pick(DUNE_ID))))

    # Execute
    with recording_logs(ENGINE_LOGGER) as recorder:
        engine.pick(CANDIDATES, CONTEXT)

    # Assert
    assert recorder.entries() == []


def test_having_no_candidates_logs_nothing() -> None:
    # Setup
    engine = an_engine(FakeChatModel(picks_reply()))

    # Execute
    with recording_logs(ENGINE_LOGGER) as recorder:
        engine.pick([], CONTEXT)

    # Assert
    assert recorder.entries() == []
