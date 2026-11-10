from typing import Protocol

from stash.domain import Item
from stash.planning.results import ProposedStep


class StepProposals(Protocol):
    def propose(self, item: Item) -> tuple[ProposedStep, ...]: ...
