from fakes.store_factories import FreshStore


class DeleteFailed(Exception):
    pass


class FailingDeleteStore(FreshStore):
    def __init__(self) -> None:
        super().__init__()
        self.fail_next_delete = True

    def delete_item_if_untouched(self, item_id: str) -> bool:
        if self.fail_next_delete:
            self.fail_next_delete = False
            raise DeleteFailed(item_id)
        return super().delete_item_if_untouched(item_id)
