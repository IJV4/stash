from collections.abc import Sequence
from typing import Protocol

from stash.domain import Item
from stash.suggestions.results import Picked, Suggestion, Unavailable


class SuggestionPicker(Protocol):
    def pick(
        self, candidates: Sequence[Item], context: str, limit: int
    ) -> tuple[Suggestion, ...]: ...


class PickDesk(Protocol):
    def suggest(self, context: str, limit: int) -> Picked | Unavailable: ...
