import threading
from collections.abc import Mapping

LATEST_RELEASE_SECONDS = 1.0


class HangingExtract:
    def __init__(self) -> None:
        self.release = threading.Event()

    def __call__(self, url: str) -> Mapping[str, object]:
        self.release.wait(LATEST_RELEASE_SECONDS)
        return {"title": "Late title"}
