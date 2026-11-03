import threading
from collections.abc import Sequence

from stash.capture import ProcessResult


class ThreadNotingRetrier:
    def __init__(self, results: Sequence[ProcessResult] = ()) -> None:
        self.results = list(results)
        self.threads: list[int] = []

    def retry_pending(self) -> list[ProcessResult]:
        self.threads.append(threading.get_ident())
        return list(self.results)
