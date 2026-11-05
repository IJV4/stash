from fakes.memory_store import MemoryStore

from stash.domain import Item, Outcome


class CompletionFailed(Exception):
    pass


class FailingCompletionStore(MemoryStore):
    def __init__(self) -> None:
        super().__init__()
        self.fail_next_completion = False

    def record_completion(self, item: Item, outcome: Outcome) -> None:
        if self.fail_next_completion:
            self.fail_next_completion = False
            raise CompletionFailed(item.id)
        super().record_completion(item, outcome)
