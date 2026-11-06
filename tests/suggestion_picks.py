from suggestion_builders import a_want_to

from stash.domain import Pick
from stash.suggestions import Picked


def a_pick(item_id: str = "i1", title: str = "Dune", reason: str = "A quiet read") -> Pick:
    return Pick(a_want_to(item_id, title=title), reason)


def picked(count: int) -> Picked:
    return Picked(tuple(a_pick(f"i{n}", f"Title {n}", f"Reason {n}") for n in range(count)))
