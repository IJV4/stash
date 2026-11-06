import asyncio
import threading

import pytest
from fakes.failing_suggester import FailingSuggester
from fakes.fake_suggestion_desk import FakeSuggestionDesk
from fakes.thread_noting_suggester import ThreadNotingSuggester
from suggestion_picks import a_pick

from stash.hermes_adapter.ports import Suggester
from stash.hermes_adapter.suggest_command import SuggestCommand
from stash.suggestions import ContextTooLong, Picked, Unavailable
from stash.suggestions.results import SUGGESTION_LIMIT


def run(suggester: Suggester, raw_args: str = "") -> str:
    return asyncio.run(SuggestCommand(suggester).run(raw_args))


def test_each_pick_is_answered_as_a_bullet_with_its_title_and_reason() -> None:
    # Setup
    desk = FakeSuggestionDesk(
        Picked((a_pick("d1", "Dune", "A quiet read"), a_pick("r1", "Ramen", "Close by")))
    )

    # Execute
    text = run(desk)

    # Assert
    assert text.splitlines() == ["• Dune — A quiet read", "• Ramen — Close by"]


def test_the_desk_is_asked_for_the_suggestion_limit() -> None:
    # Setup
    desk = FakeSuggestionDesk(Picked(()))

    # Execute
    run(desk)

    # Assert
    assert [limit for _, limit in desk.asked] == [SUGGESTION_LIMIT]


def test_the_words_after_the_command_are_the_context_and_the_limit_is_three() -> None:
    # Setup
    desk = FakeSuggestionDesk(Picked(()))

    # Execute
    run(desk, "2h free Saturday, at home")

    # Assert
    assert desk.asked == [("2h free Saturday, at home", 3)]


def test_the_command_alone_asks_with_no_context() -> None:
    # Setup
    desk = FakeSuggestionDesk(Picked(()))

    # Execute
    run(desk)

    # Assert
    assert desk.asked == [("", 3)]


def test_no_picks_are_answered_as_nothing_to_suggest() -> None:
    # Execute
    text = run(FakeSuggestionDesk(Picked(())))

    # Assert
    assert text == "Nothing to suggest right now."


def test_an_unavailable_model_is_answered_as_unavailable() -> None:
    # Execute
    text = run(FakeSuggestionDesk(Unavailable()))

    # Assert
    assert text == "Suggestions are unavailable right now."


def test_a_context_that_is_too_long_is_answered_with_the_refusal() -> None:
    # Execute
    text = run(FailingSuggester(ContextTooLong()), "x" * 501)

    # Assert
    assert text == "context must be at most 500 characters"


def test_a_long_title_and_reason_are_cut_to_the_line_limit() -> None:
    # Execute
    text = run(FakeSuggestionDesk(Picked((a_pick("d1", "T" * 120, "R" * 200),))))

    # Assert
    assert len(text) <= 300


def test_the_desk_is_asked_off_the_event_loop_thread() -> None:
    # Setup
    suggester = ThreadNotingSuggester()

    async def scenario() -> int:
        await SuggestCommand(suggester).run("")
        return threading.get_ident()

    # Execute
    loop_thread = asyncio.run(scenario())

    # Assert
    assert [thread != loop_thread for thread in suggester.threads] == [True]


def test_a_suggester_that_fails_unexpectedly_lets_the_failure_propagate() -> None:
    # Execute / Assert
    with pytest.raises(RuntimeError, match="database is closed"):
        run(FailingSuggester(RuntimeError("database is closed")))
