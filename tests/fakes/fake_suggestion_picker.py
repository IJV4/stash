from collections.abc import Sequence

from stash.domain import Item
from stash.llm import LlmError
from stash.suggestions import Suggestion


class FakeSuggestionPicker:
    def __init__(
        self, suggestions: Sequence[Suggestion] = (), error: LlmError | None = None
    ) -> None:
        self._suggestions = tuple(suggestions)
        self._error = error
        self.calls: list[tuple[tuple[Item, ...], str, int]] = []

    def pick(self, candidates: Sequence[Item], context: str, limit: int) -> tuple[Suggestion, ...]:
        self.calls.append((tuple(candidates), context, limit))
        if self._error is not None:
            raise self._error
        return self._suggestions
