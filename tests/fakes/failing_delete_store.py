from fakes.memory_store import MemoryStore


class DeleteFailed(Exception):
    pass


class FailingDeleteStore(MemoryStore):
    def __init__(self) -> None:
        super().__init__()
        self.fail_next_delete = True

    def delete_item(self, item_id: str) -> None:
        if self.fail_next_delete:
            self.fail_next_delete = False
            raise DeleteFailed(item_id)
        super().delete_item(item_id)
