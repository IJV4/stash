import threading

from stash.suggestions import Picked, Unavailable


class ThreadNotingSuggester:
    def __init__(self) -> None:
        self.threads: list[int] = []

    def suggest(self, context: str, limit: int) -> Picked | Unavailable:
        self.threads.append(threading.get_ident())
        return Picked(())
