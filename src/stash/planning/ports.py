from typing import Protocol

from stash.domain import Item
from stash.planning.results import ProposedStep


class ProposalDeclines(Protocol):
    def is_declined(self, item: Item) -> bool: ...

    def record(self, item: Item) -> None: ...


class StepProposals(Protocol):
    def propose(self, item: Item) -> tuple[ProposedStep, ...]: ...
