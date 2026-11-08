from fakes.store_factories import FreshStore

from stash.domain import Outcome


class OutcomeSaveCountingStore(FreshStore):
    def __init__(self) -> None:
        super().__init__()
        self.outcome_saves = 0

    def save_outcome(self, outcome: Outcome) -> None:
        self.outcome_saves += 1
        super().save_outcome(outcome)
