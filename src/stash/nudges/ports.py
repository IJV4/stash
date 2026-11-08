from typing import Protocol

from stash.domain import Pick


class PickSource(Protocol):
    def picks(self, context: str, limit: int) -> tuple[Pick, ...]: ...
