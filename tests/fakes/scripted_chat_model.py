import copy
from collections.abc import Mapping, Sequence

from stash.llm import ChatMessage, LlmError


class ScriptedChatModel:
    def __init__(self, outcomes: Sequence[Mapping[str, object] | LlmError]) -> None:
        self._outcomes = list(outcomes)
        self.calls: list[list[ChatMessage]] = []

    def complete_json(
        self,
        messages: Sequence[ChatMessage],
        schema: Mapping[str, object],
        schema_name: str,
    ) -> dict[str, object]:
        self.calls.append(list(messages))
        outcome = self._outcomes[len(self.calls) - 1]
        if isinstance(outcome, LlmError):
            raise outcome
        return copy.deepcopy(dict(outcome))
