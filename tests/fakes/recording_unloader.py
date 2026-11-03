from collections.abc import Callable


class RecordingUnloader:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.unloads = 0
        self.observers: list[Callable[[], None]] = []

    def unload(self) -> None:
        self.unloads += 1
        for observe in self.observers:
            observe()
        if self.error is not None:
            raise self.error
