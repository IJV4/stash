import logging
from collections.abc import Sequence
from typing import assert_never

from stash.domain import Item, Pick, Stage
from stash.llm import LlmUnavailable
from stash.store.port import Store
from stash.suggestions.ports import PickDesk, SuggestionPicker
from stash.suggestions.results import (
    CONTEXT_LIMIT,
    ContextTooLong,
    Picked,
    Suggestion,
    Unavailable,
)

CANDIDATE_LIMIT = 40

logger = logging.getLogger(__name__)


class SuggestionDesk:
    def __init__(self, store: Store, engine: SuggestionPicker) -> None:
        self._store = store
        self._engine = engine

    def suggest(self, context: str, limit: int) -> Picked | Unavailable:
        trimmed = context.strip()
        if len(trimmed) > CONTEXT_LIMIT:
            raise ContextTooLong
        candidates = self._store.list_items(stage=Stage.WANT_TO, limit=CANDIDATE_LIMIT)
        try:
            suggestions = self._engine.pick(candidates, trimmed, limit)
        except LlmUnavailable as error:
            logger.warning("suggestions unavailable: %s", error)
            return Unavailable()
        return Picked(_picks(suggestions, candidates))


class QuietPicks:
    def __init__(self, desk: PickDesk) -> None:
        self._desk = desk

    def picks(self, context: str, limit: int) -> tuple[Pick, ...]:
        match self._desk.suggest(context, limit):
            case Picked(picks=picks):
                return picks
            case Unavailable():
                return ()
            case answer:
                assert_never(answer)


def _picks(suggestions: Sequence[Suggestion], candidates: Sequence[Item]) -> tuple[Pick, ...]:
    by_id = {candidate.id: candidate for candidate in candidates}
    return tuple(Pick(by_id[suggestion.item_id], suggestion.reason) for suggestion in suggestions)
