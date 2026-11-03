import copy
from collections.abc import Mapping, Sequence

from stash.llm import ChatMessage, LlmError


class FakeChatModel:
    def __init__(
        self,
        reply: Mapping[str, object] | None = None,
        error: LlmError | None = None,
    ) -> None:
        self._reply: Mapping[str, object] = {} if reply is None else reply
        self._error = error
        self.calls: list[list[ChatMessage]] = []
        self.schema_names: list[str] = []

    def complete_json(
        self,
        messages: Sequence[ChatMessage],
        schema: Mapping[str, object],
        schema_name: str,
    ) -> dict[str, object]:
        self.calls.append(list(messages))
        self.schema_names.append(schema_name)
        if self._error is not None:
            raise self._error
        return copy.deepcopy(dict(self._reply))
