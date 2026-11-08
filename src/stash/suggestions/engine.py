import logging
from collections.abc import Callable, Sequence
from datetime import datetime
from zoneinfo import ZoneInfo

from stash.config import LlmTask
from stash.domain import Item, require_aware
from stash.llm import LlmBadOutput, ModelSource
from stash.suggestions.parse import parse_suggestions
from stash.suggestions.prompt import build_suggestion_messages
from stash.suggestions.results import SUGGESTION_LIMIT, Suggestion
from stash.suggestions.schema import SCHEMA_NAME, SUGGESTIONS_SCHEMA

logger = logging.getLogger(__name__)


class SuggestionEngine:
    def __init__(
        self,
        models: ModelSource,
        clock: Callable[[], datetime],
        timezone: ZoneInfo,
    ) -> None:
        self._models = models
        self._clock = clock
        self._timezone = timezone

    def pick(
        self, candidates: Sequence[Item], context: str, limit: int = SUGGESTION_LIMIT
    ) -> tuple[Suggestion, ...]:
        if limit < 1:
            raise ValueError("limit must be at least 1")
        if not candidates:
            return ()
        now = self._clock()
        require_aware("clock", now)
        model = self._models.model_for(LlmTask.SUGGESTIONS, now)
        today = now.astimezone(self._timezone).date()
        messages = build_suggestion_messages(candidates, context, today, limit)
        try:
            answer = model.complete_json(messages, SUGGESTIONS_SCHEMA, SCHEMA_NAME)
        except LlmBadOutput as error:
            logger.warning("suggestion model gave unusable output: %s", type(error).__name__)
            return ()
        suggestions = parse_suggestions(answer, {candidate.id for candidate in candidates}, limit)
        if not suggestions:
            logger.warning("suggestion model gave no usable pick")
        return suggestions
