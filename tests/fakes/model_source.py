import datetime as dt

from stash.config import LlmTask
from stash.llm import ChatModel, LlmError


class FakeModelSource:
    def __init__(self, model: ChatModel, error: LlmError | None = None) -> None:
        self._model = model
        self._error = error
        self.requests: list[tuple[LlmTask, dt.datetime]] = []

    def model_for(self, task: LlmTask, now: dt.datetime) -> ChatModel:
        self.requests.append((task, now))
        if self._error is not None:
            raise self._error
        return self._model
