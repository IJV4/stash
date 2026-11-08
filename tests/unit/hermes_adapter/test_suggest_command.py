import asyncio

import pytest
from fakes.failing_suggester import FailingSuggester

from stash.hermes_adapter.ports import Suggester
from stash.hermes_adapter.suggest_command import SuggestCommand
from stash.suggestions import ContextTooLong


def run(suggester: Suggester, raw_args: str = "") -> str:
    return asyncio.run(SuggestCommand(suggester).run(raw_args))


def test_a_context_that_is_too_long_is_answered_with_the_refusal() -> None:
    # Execute
    text = run(FailingSuggester(ContextTooLong()), "x" * 501)

    # Assert
    assert text == "context must be at most 500 characters"


def test_a_suggester_that_fails_unexpectedly_lets_the_failure_propagate() -> None:
    # Execute / Assert
    with pytest.raises(RuntimeError, match="database is closed"):
        run(FailingSuggester(RuntimeError("database is closed")))
