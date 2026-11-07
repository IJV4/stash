from dataclasses import dataclass

from stash.domain import Person


@dataclass(frozen=True, slots=True)
class Resolution:
    linked: tuple[Person, ...]
    unknown: tuple[str, ...]
