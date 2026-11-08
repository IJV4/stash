from fakes.store_factories import FreshStore

from stash.domain import CaptureStatus


class StatusWriteFailed(Exception):
    pass


class FailingStatusStore(FreshStore):
    def __init__(self) -> None:
        super().__init__()
        self.fail_next_status_write = False

    def set_capture_status(self, capture_id: str, status: CaptureStatus) -> None:
        if self.fail_next_status_write:
            self.fail_next_status_write = False
            raise StatusWriteFailed(capture_id)
        super().set_capture_status(capture_id, status)
