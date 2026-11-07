from typing import Any

from builders import BASE
from capture_builders import sequential_ids
from fakes.memory_store import MemoryStore

from stash.domain import KeyDate, KeyDateKind, Person
from stash.people import PeopleDirectory
from stash.store import Store


def a_person(**overrides: Any) -> Person:
    fields: dict[str, Any] = {
        "id": "p1",
        "name": "Ana Rivera",
        "relation": "sister",
        "aliases": ("Anita",),
        "notes": "Loves ceramics",
        "created_at": BASE,
    }
    return Person(**{**fields, **overrides})


def a_key_date(**overrides: Any) -> KeyDate:
    fields: dict[str, Any] = {
        "id": "k1",
        "person_id": "p1",
        "kind": KeyDateKind.BIRTHDAY,
        "label": "Birthday",
        "month": 3,
        "day": 14,
        "year": 1990,
    }
    return KeyDate(**{**fields, **overrides})


def stored_person(store: Store, **overrides: Any) -> Person:
    person = a_person(**overrides)
    store.save_person(person)
    return person


def ids_of_people(people: list[Person]) -> list[str]:
    return [person.id for person in people]


def a_directory(store: MemoryStore | None = None) -> PeopleDirectory:
    return PeopleDirectory(
        MemoryStore() if store is None else store, sequential_ids(), lambda: BASE
    )
