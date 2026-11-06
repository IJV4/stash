from collections.abc import Sequence

from stash.domain import Pick


class FakePickSource:
    def __init__(self, picks: Sequence[Pick] = ()) -> None:
        self._picks = tuple(picks)
        self.asked: list[tuple[str, int]] = []

    def picks(self, context: str, limit: int) -> tuple[Pick, ...]:
        self.asked.append((context, limit))
        return self._picks
