from stash.suggestions import Picked, Unavailable


class FakeSuggestionDesk:
    def __init__(self, answer: Picked | Unavailable) -> None:
        self._answer = answer
        self.asked: list[tuple[str, int]] = []

    def suggest(self, context: str, limit: int) -> Picked | Unavailable:
        self.asked.append((context, limit))
        return self._answer
