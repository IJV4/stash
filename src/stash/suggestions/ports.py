import datetime as dt
from collections.abc import Sequence
from typing import Protocol

from stash.config import LlmTask
from stash.domain import Item, Stage
from stash.llm import ChatModel
from stash.suggestions.results import Picked, Suggestion, Unavailable


class SuggestionModelSource(Protocol):
    def model_for(self, task: LlmTask, now: dt.datetime) -> ChatModel: ...


class CandidateStore(Protocol):
    def list_items(self, *, stage: Stage, limit: int) -> list[Item]: ...


class SuggestionPicker(Protocol):
    def pick(
        self, candidates: Sequence[Item], context: str, limit: int
    ) -> tuple[Suggestion, ...]: ...


class PickDesk(Protocol):
    def suggest(self, context: str, limit: int) -> Picked | Unavailable: ...
