import datetime as dt
from collections.abc import Sequence
from typing import Protocol

from stash.config import LlmTask
from stash.domain import Item, Step
from stash.llm import ChatModel
from stash.planning.results import ProposedStep


class DeclineSettings(Protocol):
    def get_setting(self, key: str) -> str | None: ...

    def put_setting(self, key: str, value: str) -> None: ...


class ProposalDeclines(Protocol):
    def is_declined(self, item: Item) -> bool: ...

    def record(self, item: Item) -> None: ...


class PlanningStore(Protocol):
    def get_item(self, item_id: str) -> Item | None: ...

    def steps_for(self, item_id: str) -> list[Step]: ...

    def save_steps(self, item_id: str, steps: Sequence[Step]) -> None: ...

    def save_step(self, step: Step) -> None: ...

    def get_step(self, step_id: str) -> Step | None: ...


class StepProposals(Protocol):
    def propose(self, item: Item) -> tuple[ProposedStep, ...]: ...


class PlanningModelSource(Protocol):
    def model_for(self, task: LlmTask, now: dt.datetime) -> ChatModel: ...
