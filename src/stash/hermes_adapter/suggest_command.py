import asyncio
from typing import assert_never

from stash.capture import pick_line
from stash.hermes_adapter.ports import Suggester
from stash.rendering import NO_SUGGESTIONS, SUGGESTIONS_UNAVAILABLE
from stash.suggestions.results import SUGGESTION_LIMIT, ContextTooLong, Picked, Unavailable


class SuggestCommand:
    def __init__(self, suggester: Suggester) -> None:
        self._suggester = suggester

    async def run(self, raw_args: str) -> str:
        try:
            answer = await asyncio.to_thread(self._suggester.suggest, raw_args, SUGGESTION_LIMIT)
        except ContextTooLong as refusal:
            return str(refusal)
        match answer:
            case Picked(picks=picks):
                lines = [pick_line(pick) for pick in picks]
                return "\n".join(lines) if lines else NO_SUGGESTIONS
            case Unavailable():
                return SUGGESTIONS_UNAVAILABLE
            case _:
                assert_never(answer)
