import threading
from datetime import date

from stash.library_html import RenderedLibrary


class RecordingLibraryDocuments:
    def __init__(
        self,
        html: str = "<p>library</p>",
        day: date = date(2026, 11, 2),
        keep_failure: Exception | None = None,
    ) -> None:
        self._keep_failure = keep_failure
        self._library = RenderedLibrary(html, day)
        self.kept: list[bytes] = []
        self.threads: list[int] = []

    def rendered_library(self) -> RenderedLibrary:
        self.threads.append(threading.get_ident())
        return self._library

    def keep_library_copy(self, data: bytes) -> None:
        self.threads.append(threading.get_ident())
        if self._keep_failure is not None:
            raise self._keep_failure
        self.kept.append(data)
