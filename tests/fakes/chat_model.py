import copy
from collections.abc import Mapping, Sequence

from stash.llm import ChatMessage, LlmError


class FakeChatModel:
    def __init__(
        self,
        reply: Mapping[str, object] | None = None,
        error: LlmError | None = None,
    ) -> None:
        self.reply: Mapping[str, object] = {} if reply is None else reply
        self.error = error
        self.calls: list[list[ChatMessage]] = []
        self.schemas: list[Mapping[str, object]] = []
        self.schema_names: list[str] = []

    def complete_json(
        self,
        messages: Sequence[ChatMessage],
        schema: Mapping[str, object],
        schema_name: str,
    ) -> dict[str, object]:
        self.calls.append(list(messages))
        self.schemas.append(schema)
        self.schema_names.append(schema_name)
        if self.error is not None:
            raise self.error
        return copy.deepcopy(dict(self.reply))
