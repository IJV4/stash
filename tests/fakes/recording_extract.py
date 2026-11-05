from collections.abc import Mapping


class RecordingExtract:
    def __init__(
        self,
        title: str = "Ramen crawl",
        uploader: str | None = None,
        duration: float | None = None,
    ) -> None:
        self.asked: list[str] = []
        self._described: dict[str, object] = {
            key: value
            for key, value in (("title", title), ("uploader", uploader), ("duration", duration))
            if value is not None
        }

    def __call__(self, url: str) -> Mapping[str, object]:
        self.asked.append(url)
        return self._described
