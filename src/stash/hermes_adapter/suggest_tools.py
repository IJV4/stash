import logging
from collections.abc import Sequence
from typing import Any, assert_never

from stash.domain import Pick
from stash.hermes_adapter.ports import Suggester
from stash.hermes_adapter.tool_arguments import ToolArguments
from stash.hermes_adapter.tool_json import UNREADABLE, answering, error, labelled
from stash.hermes_adapter.tool_schema import tool_schema
from stash.hermes_adapter.tool_spec import ToolSpec
from stash.rendering import SUGGESTIONS_UNAVAILABLE
from stash.suggestions.results import CONTEXT_LIMIT, SUGGESTION_LIMIT, Picked, Unavailable

logger = logging.getLogger(__name__)

SUGGEST_DESCRIPTION = (
    f"Suggest up to {SUGGESTION_LIMIT} of the owner's Want to items that fit a moment, each "
    f"with a reason. Pass what the owner said about their time and mood as the context."
)
SUGGEST_SCHEMA: dict[str, Any] = tool_schema(
    "stash_suggest",
    SUGGEST_DESCRIPTION,
    {
        "context": {
            "type": "string",
            "maxLength": CONTEXT_LIMIT,
            "description": "E.g. '2h free Saturday, at home'; may be left out.",
        }
    },
    [],
    subject="Item titles and the context",
)


def suggestions_answer(picks: Sequence[Pick]) -> str:
    return labelled(
        {
            "suggestions": [
                {"item_id": pick.item.id, "title": pick.item.title, "reason": pick.reason}
                for pick in picks
            ]
        }
    )


class SuggestTools:
    def __init__(self, suggester: Suggester) -> None:
        self._suggester = suggester

    def specs(self) -> tuple[ToolSpec, ...]:
        return (ToolSpec(SUGGEST_SCHEMA, self.suggest),)

    def suggest(self, args: object, **kwargs: object) -> str:
        return answering(args, UNREADABLE, self._suggest, logger)

    def _suggest(self, arguments: ToolArguments) -> str:
        match self._suggester.suggest(arguments.optional_text("context"), SUGGESTION_LIMIT):
            case Picked(picks=picks):
                return suggestions_answer(picks)
            case Unavailable():
                return error(SUGGESTIONS_UNAVAILABLE)
            case answer:
                assert_never(answer)
