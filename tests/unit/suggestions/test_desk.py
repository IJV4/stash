import logging

import pytest
from builders import store_holding
from fakes.fake_suggestion_picker import FakeSuggestionPicker
from log_records import recording_logs
from suggestion_builders import (
    CONTEXT,
    DUNE_ID,
    RAMEN_ID,
    a_want_to,
    want_to_items_oldest_first,
)

from stash.domain import Pick, Stage
from stash.llm import LlmDeferred, LlmUnavailable
from stash.suggestions import (
    CONTEXT_LIMIT,
    ContextTooLong,
    Picked,
    Suggestion,
    SuggestionDesk,
    Unavailable,
)
from stash.suggestions.results import SUGGESTION_LIMIT


def test_the_engine_is_offered_the_want_to_items_and_no_others() -> None:
    # Setup
    store = store_holding(a_want_to(DUNE_ID), a_want_to("later", stage=Stage.INBOX))
    picker = FakeSuggestionPicker()

    # Execute
    SuggestionDesk(store, picker).suggest(CONTEXT, SUGGESTION_LIMIT)

    # Assert
    assert [item.id for item in picker.calls[0][0]] == [DUNE_ID]


def test_the_engine_is_offered_the_newest_forty_want_to_items() -> None:
    # Setup
    store = store_holding(*want_to_items_oldest_first(45))
    picker = FakeSuggestionPicker()

    # Execute
    SuggestionDesk(store, picker).suggest(CONTEXT, SUGGESTION_LIMIT)

    # Assert
    assert [item.id for item in picker.calls[0][0]] == [f"item{n}" for n in range(44, 4, -1)]


def test_the_engine_is_given_the_context_without_surrounding_whitespace() -> None:
    # Setup
    picker = FakeSuggestionPicker()

    # Execute
    SuggestionDesk(store_holding(a_want_to()), picker).suggest(f"  {CONTEXT}\n", SUGGESTION_LIMIT)

    # Assert
    assert picker.calls[0][1] == CONTEXT


def test_the_engine_is_given_the_limit() -> None:
    # Setup
    picker = FakeSuggestionPicker()

    # Execute
    SuggestionDesk(store_holding(a_want_to()), picker).suggest(CONTEXT, limit=2)

    # Assert
    assert picker.calls[0][2] == 2


def test_suggestions_become_picks_of_the_matching_items_in_the_order_given() -> None:
    # Setup
    dune, ramen = a_want_to(DUNE_ID), a_want_to(RAMEN_ID)
    picker = FakeSuggestionPicker([Suggestion(RAMEN_ID, "Hot"), Suggestion(DUNE_ID, "Quiet")])

    # Execute
    answer = SuggestionDesk(store_holding(dune, ramen), picker).suggest(CONTEXT, SUGGESTION_LIMIT)

    # Assert
    assert answer == Picked((Pick(ramen, "Hot"), Pick(dune, "Quiet")))


def test_with_no_suggestions_the_answer_is_an_empty_picked() -> None:
    # Execute
    answer = SuggestionDesk(store_holding(a_want_to()), FakeSuggestionPicker()).suggest(
        CONTEXT, SUGGESTION_LIMIT
    )

    # Assert
    assert answer == Picked(())


def test_with_no_want_to_items_the_answer_is_an_empty_picked() -> None:
    # Execute
    answer = SuggestionDesk(store_holding(), FakeSuggestionPicker()).suggest(
        CONTEXT, SUGGESTION_LIMIT
    )

    # Assert
    assert answer == Picked(())


@pytest.mark.parametrize("error", [LlmUnavailable("down"), LlmDeferred("busy")], ids=repr)
def test_a_model_that_cannot_be_reached_makes_the_answer_unavailable(
    error: LlmUnavailable,
) -> None:
    # Setup
    desk = SuggestionDesk(store_holding(a_want_to()), FakeSuggestionPicker(error=error))

    # Execute
    answer = desk.suggest(CONTEXT, SUGGESTION_LIMIT)

    # Assert
    assert answer == Unavailable()


def test_a_context_over_the_limit_is_refused() -> None:
    # Setup
    desk = SuggestionDesk(store_holding(a_want_to()), FakeSuggestionPicker())

    # Execute / Assert
    with pytest.raises(ContextTooLong):
        desk.suggest("c" * (CONTEXT_LIMIT + 1), SUGGESTION_LIMIT)


def test_a_context_over_the_limit_is_refused_before_the_engine_is_asked() -> None:
    # Setup
    picker = FakeSuggestionPicker()
    desk = SuggestionDesk(store_holding(a_want_to()), picker)

    # Execute
    with pytest.raises(ContextTooLong):
        desk.suggest("c" * (CONTEXT_LIMIT + 1), SUGGESTION_LIMIT)

    # Assert
    assert picker.calls == []


def test_a_context_of_exactly_the_limit_is_accepted() -> None:
    # Setup
    picker = FakeSuggestionPicker()

    # Execute
    SuggestionDesk(store_holding(a_want_to()), picker).suggest(
        "c" * CONTEXT_LIMIT, SUGGESTION_LIMIT
    )

    # Assert
    assert len(picker.calls) == 1


def test_padding_whitespace_does_not_count_towards_the_context_limit() -> None:
    # Setup
    picker = FakeSuggestionPicker()

    # Execute
    SuggestionDesk(store_holding(a_want_to()), picker).suggest(
        " " * 100 + "c" * CONTEXT_LIMIT, SUGGESTION_LIMIT
    )

    # Assert
    assert len(picker.calls) == 1


def test_no_context_at_all_is_asked_with_an_empty_context() -> None:
    # Setup
    picker = FakeSuggestionPicker()

    # Execute
    SuggestionDesk(store_holding(a_want_to()), picker).suggest("", SUGGESTION_LIMIT)

    # Assert
    assert picker.calls[0][1] == ""


@pytest.mark.parametrize("error", [LlmUnavailable("down"), LlmDeferred("busy")], ids=repr)
def test_an_unavailable_model_is_logged_as_a_warning(error: LlmUnavailable) -> None:
    # Setup
    desk = SuggestionDesk(store_holding(a_want_to()), FakeSuggestionPicker(error=error))

    # Execute
    with recording_logs("stash.suggestions.desk") as recorder:
        desk.suggest(CONTEXT, SUGGESTION_LIMIT)

    # Assert
    assert recorder.entries() == [(logging.WARNING, f"suggestions unavailable: {error}")]
