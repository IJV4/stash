from collections.abc import Mapping


class RecordingExtract:
    def __init__(self, title: str = "Ramen crawl") -> None:
        self.asked: list[str] = []
        self._title = title

    def __call__(self, url: str) -> Mapping[str, object]:
        self.asked.append(url)
        return {"title": self._title}
