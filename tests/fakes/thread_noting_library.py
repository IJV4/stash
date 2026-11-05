import threading

from stash.lifecycle import LibraryEntry, LibraryQuery
from stash.lifecycle.query import DEFAULT_LIBRARY_QUERY


class ThreadNotingLibrary:
    def __init__(self) -> None:
        self.threads: list[int] = []

    def library(self, query: LibraryQuery = DEFAULT_LIBRARY_QUERY) -> tuple[LibraryEntry, ...]:
        self.threads.append(threading.get_ident())
        return ()
