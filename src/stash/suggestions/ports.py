from collections.abc import Sequence
from typing import Protocol

from stash.domain import Item
from stash.suggestions.results import Suggestion


class SuggestionPicker(Protocol):
    def pick(
        self, candidates: Sequence[Item], context: str, limit: int
    ) -> tuple[Suggestion, ...]: ...
