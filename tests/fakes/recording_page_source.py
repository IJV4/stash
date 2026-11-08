PAGE = "<html><body>Café ⭐ Dune</body></html>"


class RecordingPageSource:
    def __init__(self, page: str = PAGE, failure: Exception | None = None) -> None:
        self.calls = 0
        self._page = page
        self._failure = failure

    def __call__(self) -> str:
        self.calls += 1
        if self._failure is not None:
            raise self._failure
        return self._page
