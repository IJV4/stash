from fakes.store_factories import FreshStore

from stash.domain import Outcome


class OutcomeQueryingStore(FreshStore):
    def __init__(self) -> None:
        super().__init__()
        self.outcome_queries: list[str] = []

    def outcomes_for(self, item_id: str) -> list[Outcome]:
        self.outcome_queries.append(item_id)
        return super().outcomes_for(item_id)
